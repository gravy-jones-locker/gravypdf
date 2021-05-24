from .words import Words
from .nest import Nest, Nested
from . import helper
from .grid import Grid
from .spokes import Spoke, Spokes
from .settings import Settings

class Table:

    def __init__(self, page, header, footer, title, settings):
        """
        Every table is immediately plotted on creation of the instance.
        """
        self.header = header
        self.footer = footer
        self.settings = settings
        self.page = page
        self.title = title.strip('\n \r')

        self.y0, self.y1 = self.footer.y0, self.header.y1

        self.find_spokes()

    def __repr__(self):
        return f'{self.title}, {self.y1}, {self.y0}'

    def find_spokes(self):
        """
        Find vertical/horizontal spokes in the table.
        """
        self.spokes = Spokes()

        # Look from right to left over known vertical (i.e. header) labels
        off_r = self.header.period
        for v_lbl in self.header.lbls[::-1]:

            # Find data - adjusting for offset each iteration
            v_data, off_r = self.get_v_spoke_data(v_lbl, off_r)

            self.spokes.add_vertical(v_lbl, v_data, self.page.words)

        x0, y1 = self.spokes.get_data_vertex()  # Cut to data limit
        h_spokes = Grid(self.page, x0, None, self.y0, y1).rows
        
        h_lbls = self.get_h_lbls(x0, y1, h_spokes)
        
        for i, h_data in enumerate(h_spokes):
            self.spokes.add_horizontal(h_data, h_lbls[i])

    def get_v_spoke_data(self, hd, off_r):
        """
        Retrieve the data below vertical spokes sorted into sub-spokes.
        """
        mid = hd.midx
            
        # Cut from just after midpoint of label to far right possible col 
        cols_r = Grid(self.page, mid+10, mid+off_r+10, self.y0, hd.y0).cols
        
        off_r = cols_r[-1].agg('midx', 'median') - mid if cols_r else 0

        if off_r < 0:  # True if rightmost col to left of lbl
            cols_l = Nest()
        else:
            # Set righthand limit then look by same amount to left
            if cols_r and cols_r[0].x0 < mid:
                cut_r = cols_r[0].x0  # True if potential overlap
            else:
                cut_r = mid
                
            cols_l = Grid(self.page, mid-off_r, cut_r, self.y0, hd.y0).cols

        return Nest(*cols_r, *cols_l), off_r

    def get_h_lbls(self, cutx, cuty, h_spokes):
        """
        Given their rough location and horizontal spokes find horizontal labels.
        """
        h_lbls = [[] for x in range(len(h_spokes))]

        lbl_grid = Grid(self.page, None, cutx, self.y0, cuty+5)
        for col in lbl_grid.cols:
            
            # Split each col into *exact*/label-friendly rows
            rows = lbl_grid.segment_col(col)

            vals = rows.snap(h_spokes, lambda x, y: abs(x.midy - y.midy))
            aggs = [x for x in rows if x not in vals][::-1] 
            
            for i, val in enumerate(vals[::-1]):
                if i != len(vals) - 1:
                    lo = vals[::-1][i+1].y0
                else:
                    lo = val.y0
                lo_aggs = [x for x in aggs if x.y0 > val.y0 and x.y1 >= lo]
                if lo_aggs:
                    val = [lo_aggs[-1], *val]
                h_lbls[i].extend(val)

        return h_lbls[::-1]

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
            "header_pattern": [r'(?:20|FY|fy)(\d\d)'],
            "word_tolerance_vertical": 5,
            "word_tolerance_horizontal": 5,
            "remove_whitespace": True
        }

        fallbacks = {
            "intersection_x_tolerance": "intersection_tolerance",
            "intersection_y_tolerance": "intersection_tolerance"
        }