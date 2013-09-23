
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

    def test_root_state_passthrough(self):
        mock_state = MagicMock()

        root = datafork.DataRoot(mock_state)
        root.fork('a')
        mock_state.fork.assert_called_with('a')

        root.transaction('b')
        mock_state.transaction.assert_called_with('b')

        root.merge_children('c', or_none='d')
        mock_state.merge_children.assert_called_with('c', or_none='d')
