
import unittest
import datafork
from mock import MagicMock


class TestRoot(unittest.TestCase):

    def test_instantiate(self):
        mock_state = MagicMock()
        root = datafork.DataRoot(mock_state)

        self.assertEqual(
            type(root.slots),
            set,
        )
        self.assertEqual(
            len(root.slots),
            0,
        )

    def test_fork(self):
        mock_root_state = MagicMock()
        mock_child_state = MagicMock()

        mock_root_state.create_child.return_value = mock_child_state
        mock_root_state.merge_children.return_value = None

        root = datafork.DataRoot(mock_root_state)

        with root.fork('owner') as child:
            self.assertTrue(
                child is mock_child_state,
            )
            self.assertTrue(
                root.current_state is mock_child_state,
            )
            self.assertTrue(
                root.root_state is mock_root_state,
            )
            mock_root_state.create_child.assert_called_with('owner')
            self.assertFalse(
                 mock_root_state.merge_children.called
            )

        self.assertFalse(
            mock_root_state.merge_children.called
        )
        self.assertTrue(
            root.current_state is mock_root_state,
        )
        self.assertTrue(
            root.root_state is mock_root_state,
        )

    def test_transaction(self):
        mock_root_state = MagicMock()
        mock_child_state = MagicMock()

        mock_root_state.create_child.return_value = mock_child_state
        mock_root_state.merge_children.return_value = None

        root = datafork.DataRoot(mock_root_state)

        with root.transaction('owner') as child:
            self.assertTrue(
                child is mock_child_state,
            )
            self.assertTrue(
                root.current_state is mock_child_state,
            )
            self.assertTrue(
                root.root_state is mock_root_state,
            )
            mock_root_state.create_child.assert_called_with('owner')
            self.assertFalse(
                 mock_root_state.merge_children.called
            )

        mock_root_state.merge_children.assert_called_with([mock_child_state])
        self.assertTrue(
            root.current_state is mock_root_state,
        )
        self.assertTrue(
            root.root_state is mock_root_state,
        )

    def test_nested_states(self):
        mock_root_state = MagicMock()
        mock_child_state = MagicMock()
        mock_grandchild_state = MagicMock()

        mock_root_state.create_child.return_value = mock_child_state
        mock_child_state.create_child.return_value = mock_grandchild_state

        root = datafork.DataRoot(mock_root_state)

        self.assertTrue(
            root.current_state is mock_root_state,
        )

        with root.fork('owner1') as child:
            self.assertTrue(
                root.current_state is mock_child_state,
            )
            with root.fork('owner2') as grandchild:
                self.assertTrue(
                    root.current_state is mock_grandchild_state,
                )
            self.assertTrue(
                root.current_state is mock_child_state,
            )

        self.assertTrue(
            root.current_state is mock_root_state,
        )
