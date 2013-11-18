
import collections

__all__ = [
    "MergeConflict",
    "ValueNotKnownError",
    "ValueAmbiguousError",
    "root",
]


class State(object):
    """
    A set of values for slots under a given root.

    During the lifetime of a root, *state* objects act as the temporary data
    storage for the values of slots. Each root has a currently-active state
    and new child states can be created and activated by making use of the
    :py:meth:`fork` method, or its smarter cousin :py:meth:`transaction`.
    """

    def __init__(self, root, parent=None, owner=None):
        self.root = root
        self.parent = parent
        self.slot_values = {}
        self.slot_positions = collections.defaultdict(lambda: set())
        self.owner = owner

    def merge_children(self, children, or_none=False):
        """
        Given an iterable of one or more child states, merge the values
        of slots in these child states back into this state.

        When all of the provided children agree on the value for a
        slot, that value will replace the existing value in this state.
        If any provided child disagrees, the slot enters the merge conflict
        state and attempts to retrieve its value will result in the
        :py:class:`ValueAmbiguousError` exception.

        If the `or_none` parameter is set to `True`, the merge will
        consider the value of each slot in *this* state in addition to the
        provided children.
        """
        if len(children) == 0:
            return

        # Make sure all of the provided children are actually children,
        # or else crazy things will happen.
        for child in children:
            if child.parent != self:
                raise Exception(
                    "Cant' merge %r into %r: not a child" % (child, self)
                )

        slots = set()
        # Add to the slot set only those keys where at least one of the
        # children has its own value.
        for child in children:
            for slot in child.slot_values.iterkeys():
                slots.add(slot)

        states = [state for state in children]
        if or_none:
            states.append(self)

        for slot in slots:
            possibles = []
            for state in states:
                slot_value = state.get_slot_value(slot)
                if isinstance(slot_value, MergeConflict):
                    # Flatten existing merge conflicts so we don't end up
                    # with them nested inside each other.
                    possibles.extend(slot_value.possibilities)
                else:
                    possibles.append(
                        MergePossibility(
                            slot_value,
                            state.get_slot_positions(slot),
                        )
                    )

            all_positions = set()
            for possible in possibles:
                all_positions.update(possible.positions)
            self.slot_positions[slot] = all_positions

            self.slot_values[slot] = slot.merge(possibles)

    def _create_child(self, owner=None):
        return State(self.root, self, owner)

    def _child_context(self, owner, auto_merge):
        previous = self.root.current_state
        new = self._create_child(owner)
        class Context(object):
            def __enter__(context):
                self.root.current_state = new
                return new
            def __exit__(context, exc_type, exc_value, traceback):
                if auto_merge and exc_type is None:
                    self.merge_children([new])
                self.root.current_state = previous
        return Context()

    def fork(self, owner=None):
        """
        Create a child state.

        This method returns a context manager that activates a child state
        but does not do any automatic merging of the child on completion.
        When using this method it is the caller's responsibility to use
        :py:meth:`merge_children` to merge down any changes made in the
        child state, if appropriate.

        To be used with a `with` block. For example:

        .. code-block:: python

            with state.fork() as child_state:
                some_slot.value = 2
                state.merge_children([child_state])
        """
        return self._child_context(owner, auto_merge=False)

    def transaction(self, owner=None):
        """
        Create a child state and automatically merge it on success.

        This is similar to :py:meth:`fork` except that upon the successful
        (i.e. non-exceptional) completion of the block it will automatically
        call :py:meth:`merge_children` to apply the changes in the block.

        This is a helper for the common case of a block whose side-effects
        must only apply when it is completely successful.
        """
        return self._child_context(owner, auto_merge=True)

    def set_slot(self, slot, value, position=None):
        self.slot_values[slot] = value
        self.slot_positions[slot] = set(
            [position] if position is not None else []
        )

    def get_slot_value(self, slot):
        # fast path: we already have a local version of this
        if slot in self.slot_values:
            return self.slot_values[slot]

        current = self
        value = Slot.NOT_KNOWN
        while current is not None:
            try:
                value = current.slot_values[slot]
                break
            except KeyError:
                current = current.parent

        # If the slot has a fork function defined, fork the value before
        # we return it. This is important if e.g. the value is some sort
        # of mutable collection, where we need to make sure that each
        # state "sees" a different collection object rather than them
        # all modifying the same one.
        if value is not Slot.NOT_KNOWN and slot.fork is not None:
            value = slot.fork(value)
            self.slot_values[slot] = value

        return value

    def get_slot_positions(self, slot):
        current = self
        while current is not None:
            try:
                return current.slot_positions[slot]
            except KeyError:
                current = self.parent
            return set()


def equality_merge(cases):
    """
    If all of the provided :py:class:`MergeCase` objects are equal, returns
    the common value. Otherwise, returns a merge conflict describing all
    of the different values.

    This is the default implementation of `merge` on :py:class:`Slot`.
    """
    all_agreed = all(
        cases[0].value == case.value
        for case in cases
    )
    if all_agreed:
        return cases[0].value
    else:
        # create a merge conflict so the caller can see all of
        # the possibilities and either fail or choose one via
        # an application-specific means.
        return MergeConflict(cases)


class Slot(object):
    """
    A container for a single value that can be changed transactionally.

    During the lifetime of a slot's root its value depends on the
    currently-active state. Once the root block terminates, the value
    is baked into the object so that it can be used independently of the
    root and its child states.

    A slot also has a set of "positions" associated with it. The `datafork`
    module itself does not care what is in this set, but callers could use
    this to keep track of where values are set in order to better understand
    the possibilities in case of a merge conflict.

    By default slot values compare and merge by equality, leading to a
    merge conflict if the value of a slot differs between two states. The
    parameter `merge` can be used to provide a different implementation of
    performing the merge (takes a set of values and returns the merged
    version, or a :py:class:`MergeConflict` if no resolution is possible.)
    """

    # we will compare by reference to this thing to detect the "don't know"
    # case.
    NOT_KNOWN = type("not_known", (object,), {
        "__repr__": lambda self: "datafork.Slot.NOT_KNOWN"
    })()

    def __init__(
        self,
        root,
        owner=None,
        initial_value=NOT_KNOWN,
        merge=equality_merge,
        fork=None,
    ):
        self.owner = owner
        self.root = root
        self.merge = merge
        self.fork = fork
        self.set_value(
            initial_value,
        )

    @property
    def value(self):
        """
        The slot's current value.

        This can be assigned as long as the slot's root is still alive, in
        which case the new value applies to the currently-active state.
        Once the root scope exits, the value is baked into the slot and
        becomes unchangable.

        If this attribute is accessed when the value is not known, the
        :py:class:`ValueNotKnownError` exception will be raised. If the
        value is not known because this slot is currently in a merge conflict
        state, the more-specific :py:class:`ValueAmbiguousError` will be
        raised.
        """
        try:
            return Slot.prepare_return_value(
                self,
                self.final_value,
            )
        except AttributeError:
            return Slot.prepare_return_value(
                self,
                self.root.current_state.get_slot_value(self),
            )

    @property
    def positions(self):
        """
        The current :py:class:`set` of positions for this slot. There will
        most be zero or one members of this set, but there can be more
        after data states have been merged.
        """
        try:
            return self.final_positions
        except AttributeError:
            return self.root.current_state.get_slot_positions(self)

    @value.setter
    def value(self, value):
        self.set_value(value)

    def set_value(self, value, position=None):
        """
        Set the slot's value and provide an optional position.

        This is equivalent to assigning to :py:attr:`value` but provides
        the extra optional parameter for setting the position for the new
        value.
        """
        if hasattr(self, "final_value"):
            # should never happen
            raise Exception(
                "Can't set value on slot %r: it has been finalized" % self,
            )
        else:
            self.root.current_state.set_slot(
                self,
                value,
                position=position,
            )

    def set_value_not_known(self, position=None):
        """
        Mark this slot has having an unknown value.

        When a slot's value is not known, attempts to read the value
        will result in a :py:class:`ValueNotKnownError` exception.
        """
        self.set_value(Slot.NOT_KNOWN, position=position)

    @property
    def value_is_known(self):
        """
        ``True`` if this slot's value is presently known, or
        ``False`` if not.

        A slot's value might be unknown if it has never been assigned, if it
        has been explicitly declared as unknown, or if the slot is currently
        in a merge conflict state.
        """
        try:
            value = self.value
        except ValueNotKnownError:
            return False
        else:
            return True

    def finalize(self):
        if not hasattr(self, "final_value"):
            self.final_value = self.root.current_state.get_slot_value(self)
        if not hasattr(self, "final_positions"):
            self.final_positions = self.root.current_state.get_slot_positions(self)
        # sever the connection from the slot to the root so that
        # the root can be garbage collected after the with block exits.
        # The slot doesn't need the root anymore.
        if hasattr(self, "root"):
            del self.root

    @classmethod
    def prepare_return_value(cls, slot, value):
        if type(value) is MergeConflict:
            raise ValueAmbiguousError(slot, value)
        elif value is cls.NOT_KNOWN:
            raise ValueNotKnownError(slot)
        else:
            return value


class Root(State):
    """
    A root context that can be used to create slots.

    :py:func:`root` is the public interface to create a root, and is intended
    to be used in a ``with`` block. Once you've established a root context
    you can create slots using the :py:meth:`slot` method.

    A root is a special kind of :py:class:`State` and thus inherits the
    state-management functions of that class.
    """
    def __init__(self, root_owner=None, slot_type=Slot):
        State.__init__(self, self, None, root_owner)
        self.current_state = self
        self.slot_type = slot_type
        self.slots = set()

    def slot(
        self,
        owner=None,
        initial_value=Slot.NOT_KNOWN,
        **kwargs
    ):
        """
        Creates a new :py:class:`Slot` in this root.

        The slot's value will remain mutable for the lifetime of the root
        context, and will be frozen upon its exit.
        """
        slot = self.slot_type(
            self,
            owner,
            initial_value,
            **kwargs
        )
        self.slots.add(slot)
        return slot

    def finalize_data(self):
        for slot in self.slots:
            slot.finalize()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.finalize_data()


def root(owner=None):
    """
    Creates and returns a context manager that provides a :py:class:`Root`
    object. Use this in a with block like this:

    .. code-block:: python

        with datafork.root():
            # etc
    """
    new = Root(root_owner=owner)
    class Context(object):
        def __enter__(self):
            return new
        def __exit__(self, exc_type, exc_value, traceback):
            new.finalize_data()
    return Context()


class MergeConflict(object):
    """
    Represents the case where :py:meth:`State.merge_children` discovers
    a conflict between the states it is provided, allowing the caller
    to investigate all of the possibilities and perhaps to choose one
    to apply using application-specific logic.
    """
    #: A sequence of :py:class:`MergeConflictPossibility` objects describing
    #: possible values.
    possibilities = []

    def __init__(self, possibilities):
        self.possibilities = possibilities

    def __repr__(self):
        return "<MergeConflict %r>" % self.possibilities


class MergePossibility(object):
    """
    Represents a single possibility in a merge, or within a
    :py:class:`MergeConflict`.
    """
    #: The value from this possibility
    value = None
    #: Set of the positions at which this possibility originated.
    positions = set()

    def __init__(self, value, positions):
        self.value = value
        self.positions = positions

    def __repr__(self):
        return "<%r at %r>" % (self.value, self.positions)

    def __eq__(self, other):
        if type(other) is type(self):
            return (
                self.value == other.value and self.positions == other.positions
            )
        elif type(other) is tuple:
            return (
                (self.value, self.positions) == other
            )
        else:
            raise NotImplementedError(
                'Cannot compare MergeConflictPossibility to %r' % type(other)
            )

    def __cmp__(self, other):
        return cmp(
            (self.value, list(sorted(self.positions))),
            (other.value, list(sorted(other.positions))),
        )


class ValueNotKnownError(Exception):
    """
    Exception that is raised when a caller attempts to access the value of a
    symbol whose value is unknown.
    """
    #: The slot that this error relates to.
    slot = None

    def __init__(self, slot):
        Exception.__init__(self, 'Slot %r value not known' % slot)
        self.slot = slot


class ValueAmbiguousError(ValueNotKnownError):
    """
    Exception that is raised when a caller attempts to access the value of a
    symbol that is in the merge conflict state.
    """
    #: The slot that this error relates to.
    slot = None
    #: A :py:class:`MergeConflict` object describing the conflict.
    conflict = None

    def __init__(self, slot, conflict):
        Exception.__init__(self, 'Slot %r value is ambiguous' % slot)
        self.slot = slot
        self.conflict = conflict
