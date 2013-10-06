
import unittest
import datafork
import collections
from mock import MagicMock


class TestState(unittest.TestCase):

    def test_init(self):
        root = MagicMock()
        parent = MagicMock()
        owner = 'owner'

        state = datafork.State(root, parent, owner)

        self.assertEqual(
            state.root,
            root,
        )
        self.assertEqual(
            state.parent,
            parent,
        )
        self.assertEqual(
            state.owner,
            owner,
        )
        self.assertTrue(
            isinstance(state.slot_values, collections.MutableMapping),
        )
        self.assertTrue(
            isinstance(state.slot_positions, collections.MutableMapping),
        )
        # slot_positions is a defaultdict that should make any element start
        # its life as an empty set.
        self.assertTrue(
            isinstance(state.slot_positions["foo"], collections.MutableSet),
        )

    def test_fork(self):
        root_state = datafork.Root()

        with root_state.fork('owner') as child_state:
            self.assertEqual(
                type(child_state),
                datafork.State,
            )
            self.assertTrue(
                root_state.current_state is child_state,
            )

        self.assertTrue(
            root_state.current_state is root_state,
        )

    def test_nested_states(self):
        root_state = datafork.Root()

        with root_state.fork('owner1') as child_state:
            self.assertTrue(
                root_state.current_state is child_state,
            )
            with child_state.fork('owner2') as grandchild_state:
                self.assertTrue(
                    root_state.current_state is grandchild_state,
                )
                # re-fork child_state
                with child_state.fork('owner3') as grandchild_state_2:
                    self.assertTrue(
                        root_state.current_state is grandchild_state_2,
                    )
                self.assertTrue(
                    root_state.current_state is grandchild_state,
                )
            self.assertTrue(
                root_state.current_state is child_state,
            )

        self.assertTrue(
            root_state.current_state is root_state,
        )


class TestStateMerge(unittest.TestCase):

    def setUp(self):
        self.mock_root = MagicMock()
        self.slot_a = MagicMock()
        self.slot_b = MagicMock()
        self.slot_c = MagicMock()
        self.slot_d = MagicMock()

    def test_single(self):
        parent = datafork.State(self.mock_root)
        parent.set_slot(self.slot_a, 1, "parent_a")
        parent.set_slot(self.slot_c, 9, "parent_c")
        child = datafork.State(self.mock_root, parent)
        child.set_slot(self.slot_a, 3, "child_a")
        child.set_slot(self.slot_b, 4, "child_b")

        parent.merge_children([child])

        self.assertEqual(
            parent.get_slot_value(self.slot_a),
            3,
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_a),
            set(["child_a"]),
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_b),
            4,
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_b),
            set(["child_b"]),
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_c),
            9,
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_c),
            set(["parent_c"]),
        )

    def test_single_or_none(self):
        parent = datafork.State(self.mock_root)
        parent.set_slot(self.slot_a, 1, "parent_a")
        parent.set_slot(self.slot_c, 9, "parent_c")
        child = datafork.State(self.mock_root, parent)
        child.set_slot(self.slot_a, 3, "child_a")
        child.set_slot(self.slot_b, 4, "child_b")

        parent.merge_children([child], or_none=True)

        conflict_a = parent.get_slot_value(self.slot_a)
        conflict_b = parent.get_slot_value(self.slot_b)
        self.assertEqual(
            type(conflict_a),
            datafork.MergeConflict,
        )
        self.assertEqual(
            conflict_a.possibilities,
            [
                (3, set(["child_a"])),
                (1, set(["parent_a"])),
            ]
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_a),
            set(["child_a", "parent_a"]),
        )
        self.assertEqual(
            type(conflict_b),
            datafork.MergeConflict,
        )
        self.assertEqual(
            conflict_b.possibilities,
            [
                (4, set(["child_b"])),
                (datafork.Slot.NOT_KNOWN, set()),
            ]
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_b),
            set(["child_b"]),
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_c),
            9,
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_c),
            set(["parent_c"]),
        )

    def test_three(self):
        parent = datafork.State(self.mock_root)
        parent.set_slot(self.slot_a, 1, "parent_a")
        parent.set_slot(self.slot_c, 9, "parent_c")
        child_1 = datafork.State(self.mock_root, parent)
        child_1.set_slot(self.slot_a, 2, "child_1_a")
        child_1.set_slot(self.slot_b, 3, "child_1_b")
        child_1.set_slot(self.slot_d, 27, "child_1_d")
        child_2 = datafork.State(self.mock_root, parent)
        child_2.set_slot(self.slot_a, 4, "child_2_a")
        child_2.set_slot(self.slot_d, 27, "child_2_d")
        child_3 = datafork.State(self.mock_root, parent)
        child_3.set_slot(self.slot_a, 5, "child_3_a")
        child_3.set_slot(self.slot_d, 27, "child_3_d")

        parent.merge_children([child_1, child_2, child_3])

        conflict_a = parent.get_slot_value(self.slot_a)
        conflict_b = parent.get_slot_value(self.slot_b)
        self.assertEqual(
            type(conflict_a),
            datafork.MergeConflict,
        )
        self.assertEqual(
            conflict_a.possibilities,
            [
                (2, set(["child_1_a"])),
                (4, set(["child_2_a"])),
                (5, set(["child_3_a"])),
            ],
        )
        self.assertEqual(
            type(conflict_b),
            datafork.MergeConflict,
        )
        self.assertEqual(
            conflict_b.possibilities,
            [
                (3, set(["child_1_b"])),
                (datafork.Slot.NOT_KNOWN, set()),
                (datafork.Slot.NOT_KNOWN, set()),
            ],
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_c),
            9,
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_d),
            27,
        )
