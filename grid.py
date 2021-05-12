from settings import Settings
from nest import Nested

class Grid:

    """
    Parent class for conceptualisation of page area as matrix of edges/cells.
    """

    def fit_grid(self, nest):
        """
        Return a version of the nest filtered to fit the grid.
        """
        return nest.filter(Nested.chk_intersection, self.y0, self.y1)

    class Settings(Settings):

        defaults = {
            "explicit_vertical_lines": [],
            "explicit_horizontal_lines": [],
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 3,
            'min_words_vertical_ratio': 0.5,
            "min_words_horizontal": 1,
            "intersection_tolerance": 3,
            "intersection_x_tolerance": None,
            "intersection_y_tolerance": None,
            "find_headers": True,
            "header_pattern": [r'(?:20|FY|fy)(\d\d)']
        }

        fallbacks = {
            "intersection_x_tolerance": "intersection_tolerance",
            "intersection_y_tolerance": "intersection_tolerance"
        }