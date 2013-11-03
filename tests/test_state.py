
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

    def test_transaction(self):
        root_state = datafork.Root()
        dummy_slot = root_state.slot()

        with root_state.transaction('owner') as child_state:
            self.assertEqual(
                type(child_state),
                datafork.State,
            )
            child_state.set_slot(dummy_slot, 12, "dummypos")
            self.assertTrue(
                root_state.current_state is child_state,
            )

        # the block completed successfully so we should've auto-merged
        self.assertEqual(
            root_state.get_slot_value(dummy_slot),
            12,
        )

        try:
            with root_state.transaction('owner') as child_state:
                self.assertEqual(
                    type(child_state),
                    datafork.State,
                )
                child_state.set_slot(dummy_slot, 15, "dummypos")
                self.assertTrue(
                    root_state.current_state is child_state,
                )
                raise Exception('dummy')
        except Exception, ex:
            self.assertEqual(
                ex.message, 'dummy'
            )

        # the block excepted so we should not have auto-merged
        self.assertEqual(
            root_state.get_slot_value(dummy_slot),
            12,
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

    def test_slot_fork(self):
        root_state = datafork.Root()
        forking_slot = MagicMock()
        non_forking_slot = MagicMock()

        non_forking_slot.fork = None
        forking_slot.fork.return_value = "forked"

        root_state.set_slot(forking_slot, "unforked")
        root_state.set_slot(non_forking_slot, "unforked")

        with root_state.fork() as child_state:
            child_forked = child_state.get_slot_value(forking_slot)
            child_unforked = child_state.get_slot_value(non_forking_slot)

        parent_forked = root_state.get_slot_value(forking_slot)
        parent_unforked = root_state.get_slot_value(non_forking_slot)

        self.assertEqual(
            parent_forked,
            "unforked",
        )
        self.assertEqual(
            parent_unforked,
            "unforked",
        )
        self.assertEqual(
            child_forked,
            "forked",
        )
        self.assertEqual(
            child_unforked,
            "unforked",
        )


class TestMergeImplementations(unittest.TestCase):

    def test_values_unequal(self):
        self.assertTrue(datafork.values_unequal(1, 2))
        self.assertFalse(datafork.values_unequal(1, 1))

    def test_equality_merge_success(self):
        self.assertEqual(
            datafork.equality_merge(
                [
                    datafork.MergePossibility(1, {}),
                ]
            ),
            1
        )
        self.assertEqual(
            datafork.equality_merge(
                [
                    datafork.MergePossibility(1, {}),
                    datafork.MergePossibility(1, {}),
                ]
            ),
            1
        )
        self.assertEqual(
            datafork.equality_merge(
                [
                    datafork.MergePossibility(1, {}),
                    datafork.MergePossibility(1, {}),
                    datafork.MergePossibility(1, {}),
                ]
            ),
            1
        )

    def test_equality_merge_conflict(self):
        conflict = datafork.equality_merge(
            [
                datafork.MergePossibility(1, {"a"}),
                datafork.MergePossibility(2, {"b"}),
            ]
        )
        self.assertEqual(
            type(conflict),
            datafork.MergeConflict,
        )
        self.assertEqual(
            len(conflict.possibilities),
            2,
        )
        seen_values = set()
        for possibility in conflict.possibilities:
            seen_values.add(possibility.value)
            self.assertTrue(
                possibility.value in (1, 2)
            )
            if possibility.value == 1:
                self.assertEqual(
                    possibility.positions,
                    {"a"},
                )
            elif possibility.value == 2:
                self.assertEqual(
                    possibility.positions,
                    {"b"},
                )
        self.assertEqual(
            seen_values,
            {1, 2}
        )

class TestStateMerge(unittest.TestCase):

    def setUp(self):
        self.mock_root = MagicMock(name='root')
        self.slot_a = MagicMock(name='slot_a')
        self.slot_b = MagicMock(name='slot_b')
        self.slot_c = MagicMock(name='slot_c')
        self.slot_d = MagicMock(name='slot_d')

        needs_merge = MagicMock(return_value=True)
        self.slot_a.needs_merge = needs_merge
        self.slot_b.needs_merge = needs_merge
        self.slot_c.needs_merge = needs_merge
        self.slot_d.needs_merge = needs_merge
        self.slot_a.merge.return_value = 'merge_a'
        self.slot_b.merge.return_value = 'merge_b'
        self.slot_c.merge.return_value = 'merge_c'
        self.slot_d.merge.return_value = 'merge_d'

    def assert_expected_merge_call(self, slot, pairs):
        # called once
        self.assertTrue(
            slot.merge.call_count == 1,
            "%r.merge was called once" % slot,
        )
        # called with one positional argument
        self.assertEqual(
            len(slot.merge.call_args[0]),
            1,
        )
        # called with no keyword arguments
        self.assertEqual(
            len(slot.merge.call_args[1]),
            0,
        )
        # all elements are MergePossibility objects
        self.assertTrue(
            all(
                type(x) is datafork.MergePossibility
                for x in slot.merge.call_args[0][0]
            )
        )
        # the elements have the values and positions we expect
        got = {
            (x.value, frozenset(x.positions))
            for x in slot.merge.call_args[0][0]
        }
        expected = {
            (x[0], frozenset(x[1]))
            for x in pairs
        }
        self.assertEqual(
            got,
            expected,
        )

    def assert_no_merge_call(self, slot):
        self.assertTrue(
            slot.merge.call_count == 0,
            "%r.merge was not called" % slot,
        )

    def test_single(self):
        parent = datafork.State(self.mock_root)
        parent.set_slot(self.slot_a, 1, "parent_a")
        parent.set_slot(self.slot_c, 9, "parent_c")
        child = datafork.State(self.mock_root, parent)
        child.set_slot(self.slot_a, 3, "child_a")
        child.set_slot(self.slot_b, 4, "child_b")

        parent.merge_children([child])

        self.assert_expected_merge_call(
            self.slot_a,
            [
                (3, {"child_a"}),
            ]
        )
        self.assert_expected_merge_call(
            self.slot_b,
            [
                (4, {"child_b"}),
            ]
        )
        self.assert_no_merge_call(
            self.slot_c,
        )

        self.assertEqual(
            parent.get_slot_value(self.slot_a),
            "merge_a",
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_b),
            "merge_b",
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_c),
            9,
        )

    def test_single_or_none(self):
        parent = datafork.State(self.mock_root)
        parent.set_slot(self.slot_a, 1, "parent_a")
        parent.set_slot(self.slot_c, 9, "parent_c")
        child = datafork.State(self.mock_root, parent)
        child.set_slot(self.slot_a, 3, "child_a")
        child.set_slot(self.slot_b, 4, "child_b")

        parent.merge_children([child], or_none=True)

        self.assert_expected_merge_call(
            self.slot_a,
            [
                (1, {"parent_a"}),
                (3, {"child_a"}),
            ]
        )
        self.assert_expected_merge_call(
            self.slot_b,
            [
                (datafork.Slot.NOT_KNOWN, set()),
                (4, {"child_b"}),
            ]
        )
        self.assert_no_merge_call(
            self.slot_c,
        )

        self.assertEqual(
            parent.get_slot_value(self.slot_a),
            "merge_a",
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_b),
            "merge_b",
        )
        self.assertEqual(
            parent.get_slot_value(self.slot_c),
            9,
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

        self.assert_expected_merge_call(
            self.slot_a,
            [
                (2, {"child_1_a"}),
                (4, {"child_2_a"}),
                (5, {"child_3_a"}),
            ]
        )
        self.assert_expected_merge_call(
            self.slot_b,
            [
                (datafork.Slot.NOT_KNOWN, set()), # not set in parent
                (3, {"child_1_b"}),
            ]
        )
        self.assert_no_merge_call(
            self.slot_c,
        )
        self.assert_expected_merge_call(
            self.slot_d,
            [
                (27, {"child_1_d"}),
                (27, {"child_2_d"}),
                (27, {"child_3_d"}),
            ]
        )

        self.assertEqual(
            parent.get_slot_value(self.slot_a),
            "merge_a",
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_a),
            {
                "child_1_a",
                "child_2_a",
                "child_3_a",
            },
        )

        self.assertEqual(
            parent.get_slot_value(self.slot_b),
            "merge_b",
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_b),
            {
                "child_1_b",
            },
        )

        self.assertEqual(
            parent.get_slot_value(self.slot_c),
            9,
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_c),
            {
                "parent_c",
            },
        )

        self.assertEqual(
            parent.get_slot_value(self.slot_d),
            "merge_d",
        )
        self.assertEqual(
            parent.get_slot_positions(self.slot_d),
            {
                "child_1_d",
                "child_2_d",
                "child_3_d",
            },
        )
