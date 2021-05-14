from .grid import Grid
from .words import Words
from .nest import Nest

class Table(Grid):

    def __init__(self, page, hi, lo, title):
        """
        Store essential info and cut elements from page.
        """
        super().__init__(page, y1=hi.agg('y1', 'max'), y0=lo.agg('y0', 'min'))
        
        self.header = hi
        self.footer = lo

        self.title = title.strip('\n \r')

        self.spokes = Nest()
        self.lbls = Nest()

    def __repr__(self):
        return f'{self.title}, {self.y0}, {self.y1}'

    def find_lbls(self):
        """
        Find and distribute horizontal sublabels.
        """
        lbl_cut = self.header.lbls[0].midx - self.header.period
        lbl_sub = self.get_sub(self.x0, lbl_cut, self.y0, self.y1)

        for col in lbl_sub.w_cols[::-1]:
            col_sub = self.get_sub(col.x0, col.x1, self.y0, self.y1)

            col_lbls = col_sub.get_h_lbls()
            self.lbls.append(col_lbls)
    
    def find_v_spokes(self, off_l=0):
        """
        Find the columns of data which extend from each label in the top header
        row.
        """
        for lbl in self.header.lbls[::-1]:  # Iterate r --> l over known labels

            # Split the grid to below/right of label and look for word cols
            xr = lbl.midx + self.header.period - off_l
            r = self.get_sub(x0=lbl.midx, x1=xr, y0=self.y0, y1=lbl.y0)
            
            # Then look to the left by a corresponding amount
            off_l = self.get_lbl_off(lbl, r.w_cols, self.header.period, 'midx')

            xl = lbl.midx - self.header.period + off_l
            if xl < r.w_cols[-1].x0:
                l = self.get_sub(x0=xl, x1=r.w_cols[-1].x0, y0=self.y0, y1=lbl.y0)
                spokes = Spoke(lbl, *l.w_cols, *r.w_cols).split_v()
            else:
                spokes = Spoke(lbl, *r.w_cols).split_v()

            self.spokes.addtwigs(spokes)     

    def find_h_spokes(self):
        """
        Find and label the horizontal spokes from the position of the values.
        """
        inner = self.lbls.get_sorted(lambda x: x.x0, inv=True)

        for lbl in inner:  # Go through inner column of labels
            sub = self.get_sub(x0=lbl.x0, x1=self.x1, y0=lbl.y0, y1=lbl.y1)
            
            if len(sub.w_cols) < len(self.header.lbls):
                continue  # Ignore any without the full compliment of values  
            
            spokes = Spoke(lbl, *sub.w_cols).split_h(self.lbls, '\n')
            self.spokes.addtwigs(spokes)
        
    def get_sub(self, x0, x1, y0, y1):
        """
        Plot the columns of data which follow down from a label.
        """
        sub = Grid(self.page, x0=x0, x1=x1, y0=y0, y1=y1)
        
        sub.w_cols = sub.get_w_cols(5)
        sub.w_rows = sub.get_w_rows(5)
        
        return sub

    def get_lbl_off(self, lbl, data, period, attr):
        """
        Get the offset of the data attached to the label from the expected pos.
        """
        if len(data) == 0:  # If no data found return full period
            return period
        else:
            return lbl.midx - data[-1].agg(attr, 'median') + period

class Spoke(Nest):

    def __init__(self, lbl, *clusters):
        """
        Store constitutive spoke and label data. 
        """
        self.lbl  = lbl
        self.title = lbl.text
        
        super().__init__(*clusters)

    def split_v(self):
        """
        Split one vertical spoke into multiple subsidiaries.
        """
        return self

    def split_h(self, lbl_data, split_str):
        return self