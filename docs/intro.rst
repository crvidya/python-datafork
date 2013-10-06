Introduction: Transactions
==========================

The simplest use-case for `datafork` is to create transactional blocks whose
data changes will "stick" only if they run to completion. If any statement
in the block raises an exception, the changes within the block will be
ignored.

To get started, we must create a *root*. A root is a container for a set
of slots, with each slot belonging to exactly one root. This allows multiple
`datafork` callers in the same program without them trampling on one another.
A root can be created as follows:

.. code-block:: python

    import datafork

    with datafork.root() as root:
        pass

Within the root we can create one or more slots to represent the state of
whatever process we're dealing with:

.. code-block:: python

    import datafork

    with datafork.root() as root:
        example_slot = root.slot()
        example_slot.value = 4
        print example_slot.value

With this framework in place, we can then create a transactional block
that will modify the example slot's value only when it's successful:

.. code-block:: python

    import datafork

    with datafork.root() as root:
        example_slot = root.slot()
        example_slot.value = 4
        with root.transaction():
            example_slot.value = 3
            might_raise_exception()
        print example_slot.value

In the above example, if the `might_raise_exception` function raises an
exception, the example slot's value will be restored to 4. However, if it
returns successfully then the example slot's value will continue as 3.

