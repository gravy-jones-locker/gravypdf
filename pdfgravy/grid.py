from .settings import Settings
from .nest import Nested, Nest
from . import helper
import statistics as stats
from .words import Words

class Grid:

    """
    Parent class for conceptualisation of page area as matrix of edges/cells.
    """

    def __init__(self, page, settings, x0=None, x1=None, y0=None, y1=None):
        """
        Store position and cut relevant features from page.
        """
        self.y1 = y1 if y1 else page.h
        self.y0 = y0 if y0 else 0

        self.x1 = x1 if x1 else page.w
        self.x0 = x0 if x0 else 0

        self.words = self.get_fitted(page.words)
        self.lines = self.get_fitted(page.lines)

        if self.words:
            self.find_cols(settings['word_tolerance_vertical'])
            self.find_rows(settings['word_tolerance_horizontal'])
        else:
            self.cols, self.rows = Words(), Words()

    def get_fitted(self, nest):
        """
        Return a version of the nest filtered to fit the grid.
        """
        return nest.filter(Nested.chk_intersection, self)

    def find_cols(self, w_tol):
        """
        Use multiple clustering and subsequent separation to find cols of words.
        """
        # Cluster words by multiple x pts (l/r/mid) --> [cluster, cluster..]
        h_clusters, align = self.words.mega_cluster('horizontal', w_tol, True)

        # Then cluster each of those by their midpoint w/ large tolerance -->
        # [[cluster, cluster..], [cluster, cluster..]..]

        col_tol = stats.median([x.w for x in h_clusters]) / 2

        fn = lambda x: x.agg(align, 'median')
        self.cols = h_clusters.cluster(fn, col_tol)

        # Then take the largest of each to get one cluster for each column
        self.cols.apply_nested(Nest.get_sorted, len, 0, inv=True)

    def find_rows(self, word_tol):
        """
        As above (get_cols) but slimmed and applied vertically for rows.
        """
        rows, _ = self.words.mega_cluster('vertical', word_tol)
        
        # Take the largest cluster of rows
        self.rows = rows.get_sorted(len, 0, inv=True)

    def segment_col(self, col):
        """
        Segment a column by the horizontal position of words and lines within -
        ***which column-by-column can be assumed to take only one place*** 
        """
        out = Nest()

        # Cluster words into rows with tolerance of roughly half normal spacing
        rows = col.cluster(lambda x: x.midy, (col.y1 - col.y0) / len(col) / 2)
        
        lns = self.lines_h.slice(x0=col.x0, x1=col.x1)
        words = self.words.slice(x0=col.x0, x1=col.x1)
        
        for i, ln in enumerate(lns[:-1]):
            y1 = ln.y1
            y0 = self.lines_h[i+1].y0

            # Compile a value from all the words inside a pair of lines
            val = words.filter(lambda x: x.y0 >= y0 and x.y1 <= y1)
            if len(val) > 0:
                out.append(val)
        
        for r in rows:  # Iterate over rows and insert any not yet covered
            if any([r.chk_intersection(x) for x in out]):
                continue
            out.append(r)

        return out

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