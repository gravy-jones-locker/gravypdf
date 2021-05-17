from .nest import Nest, Nested

class Spoke(Nest):

    def __init__(self, lbls, *clusters):
        """
        Store constitutive spoke and label data. 
        """
        self.lbls  = Nest(*sorted(lbls, key=lambda x: x.x0))
        self.title = ', '.join([x.text.strip('\n ') for x in self.lbls])

        super().__init__(*clusters)

        self.calc_orientation()

    def __repr__(self):
        return f'{self.title}: {self.midx if self.v else self.midy}'        

    def split_v(self):
        """
        Split one vertical spoke into multiple subsidiaries.
        """
        if len(self) < 2:
            self._ls = self[0]
            return Nest(self)  # True if obviously no subheaders

        out = Nest()
        for sub_spoke in self:
            sub_hd = sub_spoke.get_sorted(lambda x: x.y1, inv=True)
            vals = sub_spoke.slice(y1=sub_hd.y0)

            out.append(Spoke(*[*sub_hd, *self.lbls], *vals))
        
        return out

    def consolidate_h(self, flat_lbls):
        """
        Consolidate horizontal spokes into proper aggregates.
        """
        out = Nest()

        ad_lbls = flat_lbls.filter(Nested.chk_intersection, self, False, True)
        self.lbls._ls += [x for x in ad_lbls if x not in self.lbls]

        for sub_spoke in self:
            out.append(Spoke(self.lbls, *sub_spoke))

        return out