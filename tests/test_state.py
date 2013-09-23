
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
