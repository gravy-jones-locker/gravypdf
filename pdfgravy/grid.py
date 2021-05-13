from .settings import Settings
from .nest import Nested, Nest
from . import helper
import statistics as stats
from .words import Words

class Grid:

    """
    Parent class for conceptualisation of page area as matrix of edges/cells.
    """

    def __init__(self, page, x0=None, x1=None, y0=None, y1=None):
        """
        Store position and cut relevant features from page.
        """
        self.page = page

        self.store_pos(x0, x1, y0, y1)

        self.words = self.get_fitted(page.words)
        self.lines = self.get_fitted(page.lines)

    def store_pos(self, x0=None, x1=None, y0=None, y1=None):
        """
        Stores the coordinates of the grid in the page.
        """
        self.y1 = y1 if y1 else self.page.h
        self.y0 = y0 if y0 else 0

        self.x1 = x1 if x1 else self.page.w
        self.x0 = x0 if x0 else 0

    def get_fitted(self, nest):
        """
        Return a version of the nest filtered to fit the grid.
        """
        return nest.filter(Nested.chk_intersection, self)

    @helper.ignore_empty(chk_attr='words', out_type=Words)
    def find_w_cols(self, word_tol):
        """
        Use multiple clustering and subsequent separation to find cols of words.
        """
        # Cluster words by multiple x pts (l/r/mid) --> [cluster, cluster..]
        h_clusters = self.words.mega_cluster('horizontal', word_tol, True)

        # Then cluster each of those by their midpoint w/ large tolerance -->
        # [[cluster, cluster..], [cluster, cluster..]..]

        col_tol = stats.median([x.w for x in self.words]) / 2

        fn = lambda x: x.agg('midx', 'median')
        self.w_cols = h_clusters.cluster(fn, col_tol)

        # Then take the largest of each to get one cluster for each column
        self.w_cols.apply_nested(Nest.get_sorted, len, 0, inv=True)

    @helper.ignore_empty(chk_attr='words', out_type=Words)
    def find_w_rows(self, word_tol):
        """
        As above (find_w_cols) but slimmed and applied vertically for rows.
        """
        self.w_rows = self.words.mega_cluster('vertical', word_tol)
        
        self.w_rows.apply_nested(Nest.get_sorted, len, 0, inv=True)

    @helper.lazy_property
    def lines_h(self):
        self._lines_h = self.lines.filter(h=True)
    
    @helper.lazy_property
    def lines_v(self):
        self._lines_v = self.lines.filter(v=True)

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