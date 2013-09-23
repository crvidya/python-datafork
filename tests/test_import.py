
import unittest

class TestImport(unittest.TestCase):

    def test_import(self):
        datafork = __import__('datafork')
        # This test is here to make sure that changing the top-level public
        # API is always a concious decision.
        self.assertEqual(
            list(datafork.__all__),
            [
                'MergeConflict',
                'ValueNotKnownError',
                'ValueAmbiguousError',
                'root',
            ],
        )
