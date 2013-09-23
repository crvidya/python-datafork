
import unittest
import datafork
import collections
from mock import MagicMock


class TestState(unittest.TestCase):

    def test_init(self):
        root = MagicMock()
        parent = MagicMock()
        owner = 'owner'

        state = datafork.DataState(root, parent, owner)

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
        mock_root = MagicMock()
        root_state = datafork.DataState(mock_root)

        mock_root.current_state = root_state

        with root_state.fork('owner') as child_state:
            self.assertEqual(
                type(child_state),
                datafork.DataState,
            )
            self.assertTrue(
                mock_root.current_state is child_state,
            )

        self.assertTrue(
            mock_root.current_state is root_state,
        )

    def test_nested_states(self):
        mock_root = MagicMock()
        root_state = datafork.DataState(mock_root)

        mock_root.current_state = root_state

        with root_state.fork('owner1') as child_state:
            self.assertTrue(
                mock_root.current_state is child_state,
            )
            with child_state.fork('owner2') as grandchild_state:
                self.assertTrue(
                    mock_root.current_state is grandchild_state,
                )
                # re-fork child_state
                with child_state.fork('owner3') as grandchild_state_2:
                    self.assertTrue(
                        mock_root.current_state is grandchild_state_2,
                    )
                import logging
                logging.debug("current %r", mock_root.current_state)
                logging.debug("grandchild2 %r", grandchild_state_2)
                logging.debug("grandchild %r", grandchild_state)
                logging.debug("child %r", child_state)
                logging.debug("root %r", root_state)
                self.assertTrue(
                    mock_root.current_state is grandchild_state,
                )
            self.assertTrue(
                mock_root.current_state is child_state,
            )

        self.assertTrue(
            mock_root.current_state is root_state,
        )
