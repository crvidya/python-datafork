
import unittest
import datafork
import collections
from mock import MagicMock


class TestSlot(unittest.TestCase):

    def test_init(self):
        mock_root = MagicMock()
        mock_root.current_state = MagicMock()
        mock_root.current_state.set_slot = MagicMock()

        slot = datafork.Slot(mock_root)
        self.assertEqual(slot.owner, None)
        mock_root.current_state.set_slot.assert_called_with(
            slot,
            datafork.Slot.NOT_KNOWN,
            position=None,
        )

        slot = datafork.Slot(mock_root, owner=3)
        self.assertEqual(slot.owner, 3)

        slot = datafork.Slot(mock_root, initial_value=2)
        mock_root.current_state.set_slot.assert_called_with(
            slot,
            2,
            position=None,
        )

    def test_value(self):
        mock_root = MagicMock()
        mock_root.current_state = MagicMock()
        mock_root.current_state.get_slot_value = MagicMock()
        mock_root.current_state.get_slot_value.return_value = "hi"

        slot = datafork.Slot(mock_root)
        self.assertEqual(slot.value, "hi")
        mock_root.current_state.get_slot_value.assert_called_with(slot)

        slot.final_value = "hello"
        self.assertEqual(slot.value, "hello")
        mock_root.current_state.get_slot_value.assert_called_once_with(slot)

    def test_positions(self):
        mock_root = MagicMock()
        mock_root.current_state = MagicMock()
        mock_root.current_state.get_slot_positions = MagicMock()
        mock_root.current_state.get_slot_positions.return_value = set()

        slot = datafork.Slot(mock_root)
        self.assertEqual(slot.positions, set())
        mock_root.current_state.get_slot_positions.assert_called_with(slot)

        mock_root.current_state.get_slot_positions.return_value = set(("hi",))
        self.assertEqual(slot.positions, set(("hi",)))

        slot.final_positions = set(("hello",))
        self.assertEqual(slot.positions, set(("hello",)))

        # doesn't get called when final_positions is set, so there's a total
        # of two calls here.
        self.assertEqual(
            mock_root.current_state.get_slot_positions.call_count,
            2,
        )

    def test_set_value(self):
        mock_root = MagicMock()
        mock_root.current_state = MagicMock()
        mock_root.current_state.set_slot = MagicMock()

        slot = datafork.Slot(mock_root)
        # set_value actually gets called during __init__, so reset.
        mock_root.current_state.set_slot.reset_mock()

        slot.set_value("hi")
        mock_root.current_state.set_slot.assert_called_with(
            slot,
            "hi",
            position=None
        )
        mock_root.current_state.set_slot.reset_mock()

        slot.set_value("hello", position=3)
        mock_root.current_state.set_slot.assert_called_with(
            slot,
            "hello",
            position=3
        )
        mock_root.current_state.set_slot.reset_mock()

        slot.set_value_not_known()
        mock_root.current_state.set_slot.assert_called_with(
            slot,
            datafork.Slot.NOT_KNOWN,
            position=None
        )
        mock_root.current_state.set_slot.reset_mock()

        slot.set_value_not_known(position=20)
        mock_root.current_state.set_slot.assert_called_with(
            slot,
            datafork.Slot.NOT_KNOWN,
            position=20
        )

        slot.final_value = 2
        self.assertRaises(
            Exception,
            lambda: slot.set_value("hey")
        )

    def test_value_is_known(self):
        mock_root = MagicMock()
        slot = datafork.Slot(mock_root)

        slot.final_value = datafork.Slot.NOT_KNOWN
        self.assertFalse(
            slot.value_is_known,
        )

        slot.final_value = 1
        self.assertTrue(
            slot.value_is_known,
        )

    def test_prepare_return_value(self):
        mock_slot = MagicMock()

        self.assertEqual(
            datafork.Slot.prepare_return_value(mock_slot, 1),
            1,
        )
        self.assertRaises(
            datafork.ValueNotKnownError,
            lambda: datafork.Slot.prepare_return_value(
                mock_slot,
                datafork.Slot.NOT_KNOWN,
            ),
        )
        self.assertRaises(
            datafork.ValueAmbiguousError,
            lambda: datafork.Slot.prepare_return_value(
                mock_slot,
                datafork.MergeConflict([]),
            ),
        )
