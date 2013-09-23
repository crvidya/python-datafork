
import unittest
import datafork
from mock import MagicMock


class TestRoot(unittest.TestCase):

    def test_instantiate(self):
        root = datafork.Root('owner')

        self.assertEqual(
            type(root.slots),
            set,
        )
        self.assertEqual(
            len(root.slots),
            0,
        )
        self.assertEqual(
            root.owner,
            'owner',
        )
        # a root is its own root
        self.assertEqual(
            root.root,
            root,
        )
        # a root has no parent
        self.assertEqual(
            root.parent,
            None,
        )
        # a root's current state is initially itself
        self.assertEqual(
            root.current_state,
            root,
        )
