from .settings import Settings
from .nest import Nested, Nest
from . import helper
import statistics as stats
from .words import Words
from copy import copy

class Grid:

    """
    Parent class for conceptualisation of page area as matrix of edges/cells.
    """

    def __init__(self, page, x0=None, x1=None, y0=None, y1=None):
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
            self.find_cols(5)
            self.find_rows(5)
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
        # Cluster words by multiple x pts (l/r/mid)
        h_clusters, align = self.words.mega_cluster('horizontal', w_tol)
        h_clusters = Nest(*[x for y in h_clusters for x in y])

        # Then flatten and cluster the clusters with a wide tolerance to sort
        # by column.

        col_tol = stats.median([x.w for x in h_clusters]) / 2

        fn = lambda x: x.agg(align, 'median')
        self.cols = h_clusters.cluster(fn, col_tol)

        # Then take the largest of each to get one cluster for each column
        self.cols.apply_nested(Nest.get_sorted, len, 0, inv=True)

    def find_rows(self, w_tol):
        """
        As above (get_cols) but slimmed and applied vertically for rows.
        """
        rows, _ = self.words.mega_cluster('vertical', w_tol)
        
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
        
        lns = self.lines_h.filter(Nested.chk_intersection, col, x_only=True)
        lns = sorted(lns, key=lambda x: x.y0)
        
        for i, ln in enumerate(lns[:-1]):
            y0 = ln.y0
            y1 = lns[i+1].y1

            # Compile a value from all the words inside a pair of lines
            val = rows.filter(lambda x: x.y0 >= y0 and x.y1 <= y1)
            val.set_bbox()
            
            val.y0 = y0
            val.y1 = y1

            out.append(val)
        
        for r in rows:  # Iterate over rows and insert any not yet covered
            if any([r.chk_intersection(x) for x in out]):
                continue
            r.set_bbox()
            out.append(r)

        return out

    @helper.lazy_property
    def lines_h(self):
        self._lines_h = self.lines.filter_attrs(orientation='h')
        if not self._lines_h:
            return
        hi, lo = copy(self._lines_h[0]), copy(self._lines_h[0])
        hi.x0, hi.x1, hi.y0, hi.y1 = self.x0, self.x1, self.y1, self.y1
        lo.x0, lo.x1, lo.y0, lo.y1 = self.x0, self.x1, self.y0, self.y0
        self._lines_h.extend([hi, lo])
    
    @helper.lazy_property
    def lines_v(self):
        self._lines_v = self.lines.filter_attrs(orientation='v')