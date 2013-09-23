
import collections

__all__ = [
    "MergeConflict",
    "ValueNotKnownError",
    "ValueAmbiguousError",
    "root",
]


class State(object):

    def __init__(self, root, parent=None, owner=None):
        self.root = root
        self.parent = parent
        self.slot_values = {}
        self.slot_positions = collections.defaultdict(lambda: set())
        self.owner = owner

    def merge_children(self, children, or_none=False):
        pass

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
        return self._child_context(owner, auto_merge=False)

    def transaction(self, owner=None):
        return self._child_context(owner, auto_merge=True)

    def set_slot(self, slot, value, position=None):
        self.slot_values[slot] = value
        self.slot_positions[slot] = set(
            [position] if position is not None else []
        )

    def get_slot_value(self, slot):
        current = self
        while current is not None:
            try:
                return current.slot_values[slot]
            except KeyError:
                current = self.parent
            return Slot.NOT_KNOWN


class Slot(object):
    # we will compare by reference to this thing to detect the "don't know"
    # case.
    NOT_KNOWN = type("not_known", (object,), {})()

    def __init__(
        self,
        root,
        owner=None,
        initial_value=NOT_KNOWN,
    ):
        self.owner = owner
        self.root = root
        self.set_value(
            initial_value,
        )

    @property
    def value(self):
        try:
            return DataSlot.prepare_return_value(
                self,
                self.final_value,
            )
        except AttributeError:
            return DataSlot.prepare_return_value(
                self,
                self.root.current_state.get_slot_value(self),
            )

    @property
    def positions(self):
        try:
            return self.final_positions
        except AttributeError:
            return self.root.current_state.get_slot_positions(self)

    @value.setter
    def value(self, value):
        self.set_value(value)

    def set_value(self, value, position=None):
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
        current_data.set_slot_value(NOT_KNOWN, position=position)

    @property
    def value_is_known(self):
        try:
            self.get_value()
        except DataSlotValueNotKnownError:
            return False
        else:
            return True

    @classmethod
    def prepare_return_value(cls, slot, value):
        if type(value) is MergeConflict:
            raise DataSlotValueAmbiguousError(slot, value)
        elif value is NOT_KNOWN:
            raise DataSlotValueNotKnownError(slot)
        else:
            return value


class Root(State):
    def __init__(self, root_owner=None, slot_type=Slot):
        State.__init__(self, self, None, root_owner)
        self.current_state = self
        self.slot_type = slot_type
        self.slots = set()

    def slot(
        self,
        owner=None,
        initial_value=Slot.NOT_KNOWN,
        initial_position=None,
    ):
        """
        Creates a new slot in this root.
        """
        slot = self.slot_type(self, owner, initial_value, initial_position)
        self.slots.add(slot)
        return slot

    def slotted_object(self):
        return SlottedObject(self)

    def slotted_mapping(self):
        return SlottedMapping(self)

    def slotted_sequence(self):
        return SlottedSequence(self)

    def slotted_set(self):
        return SlottedSet(self)

    def finalize_data(self):
        for slot in self.slots:
            slot.final_value = slot.value
            slot.final_position = slot.position
            # sever the connection from the slot to the root so that
            # the root can be garbage collected after the with block exits.
            # The slot doesn't need the root anymore.
            del slot.root

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.finalize_data()


def root(owner=None):
    new = Root(root_owner=owner)
    class Context(object):
        def __enter__(self):
            return new
        def __exit__(self, exc_type, exc_value, traceback):
            new.finalize_data()
    return Context()


class MergeConflict(object):

    def __init__(self, possibilities):
        self.possibilities = possibilities

    def __repr__(self):
        return "<MergeConflict %r>" % self.possibilities


class ValueNotKnownError(Exception):
    def __init__(self, slot):
        Exception.__init__('Slot %r value not known' % slot)
        self.slot = slot


class ValueAmbiguousError(ValueNotKnownError):
    def __init__(self, slot, conflict):
        Exception.__init__('Slot %r value is ambiguous' % slot)
        self.slot = sloft
        self.conflict = conflict


class NoActiveRoot(Exception):
    pass
