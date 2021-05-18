from .nest import BasePDF, Nest, Nested

class Spoke(Nest):

    def __init__(self, lbls, *clusters):
        """
        Store constitutive spoke and label data. 
        """
        self.lbls  = Nest(*[x for x in lbls if x.text])
        self.title = ', '.join([x.text.strip('\n ') for x in self.lbls])

        super().__init__(*clusters)

        self.set_coords()
        self.calc_orientation()

        if min([x.x0 for x in self.lbls]) < self.x0:
            self.x0 = min([x.x0 for x in self.lbls])

    def __repr__(self):
        dets = f'{self.midx} (v)' if self.v else f'{self.midy} (h)'
        return f'{self.title}: {dets}'        

    def split_v(self, words):
        """
        Split one vertical spoke into multiple subsidiaries.
        """
        if len(self) < 2:
            self._ls = self[0]
            return Nest(self)  # True if obviously no subheaders

        out = Nest()
        for sub_spoke in self:
            sub_hds = words.filter(Nested.chk_intersection, sub_spoke, True)
            sub_hds = sub_hds.slice(y0=sub_spoke.y1, y1=self.lbls.y0)

            out.append(Spoke([*sub_hds, *self.lbls], *self))
        
        return out

    def consolidate_h(self, lbls):
        """
        Consolidate horizontal spokes into proper aggregates.
        """
        out = Nest()

        for x in [x for y in lbls for x in y]:  # Iterate over flattened list
            if not x.chk_intersection(self, y_only=True) or x in self.lbls:
                continue
            self.lbls.append(x)

        for sub_spoke in self:
            sub_spoke.set_coords()
            out.append(Spoke(self.lbls, *sub_spoke))

        return out