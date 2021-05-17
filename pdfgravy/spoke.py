from .nest import Nest, Nested

class Spoke(Nest):

    def __init__(self, lbls, *clusters):
        """
        Store constitutive spoke and label data. 
        """
        self.lbls  = lbls
        self.title = ', '.join(lbls)
        
        super().__init__(*clusters)

        self.calc_orientation()

    def __repr__(self):
        return f'{self.title}: {self.midx if self.v else self.midy}'

    @Nest.Decorators.rehome
    def split_v(self):
        """
        Split one vertical spoke into multiple subsidiaries.
        """
        if len(self) < 2:
            yield self  # True if obviously no subheaders

        out = Nest()
        for sub_spoke in self:
            sub_hd = sub_spoke.get_sorted(lambda x: x.y1, inv=True)
            
            vals = sub_spoke.slice(y1=sub_hd.y0)

            yield Spoke(sub_hd + self.lbls, *vals)

    @Nest.Decorators.rehome
    def consolidate_h(self, lbls):
        """
        Consolidate horizontal spokes into proper aggregates.
        """
        if len(self) > 1:
            yield from (Spoke(lbls, x).consolidate_h(lbls) for x in self)

        self.lbls += lbls.filter(Nested.chk_intersection, self)
        
        yield self