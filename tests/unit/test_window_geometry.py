import unittest

from src.core.window_geometry import Rect


class RectTests(unittest.TestCase):
    def test_dimensions_are_derived_from_edges(self):
        rect = Rect(left=-10, top=20, right=190, bottom=120)

        self.assertEqual((rect.width, rect.height), (200, 100))

    def test_rejects_empty_or_inverted_rectangles(self):
        for edges in (
            (0, 0, 0, 10),
            (0, 0, 10, 0),
            (10, 0, 0, 10),
            (0, 10, 10, 0),
        ):
            with self.subTest(edges=edges):
                with self.assertRaises(ValueError):
                    Rect(*edges)


if __name__ == "__main__":
    unittest.main()
