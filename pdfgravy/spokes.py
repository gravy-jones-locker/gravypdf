from .nest import Nest, Nested

class Spokes(Nest):

    class Decorators:

        @classmethod
        def add_spoke(decs, func):
            """
            Quick shorthand for adding spokes to the nest.
            """
            def inner(cls, *args, **kwargs):
                for elem in func(cls, *args, **kwargs):
                    cls.append(elem)
            return inner

    @Decorators.add_spoke
    def add_vertical(self, lbl, data, words):
        """
        Add vertical spokes splitting into sub-spokes as required.
        """
        if len(data) < 2:  # True if only one spoke --> no splitting
            yield Spoke([lbl], data, orientation='v', val=data.midx)
        else:
            for sub in data:
                
                # Do x-filtering then find area above col/below label
                lbls = words.filter(Nested.chk_intersection, sub, x_only=True)
                lbls = lbls.slice(y0=sub.y1, y1=lbl.y0)

                yield Spoke([lbl, *lbls], sub, orientation='v', val=sub.midx)  

    @Decorators.add_spoke
    def add_horizontal(self, data, h_lbls):
        """
        Add horizontal spokes consolidating aggregates as necessary
        """
        yield Spoke(h_lbls, data, orientation='h', val=data.midy)

    def get_data_vertex(self):
        """
        Return left/topmost point of spoke data.
        """
        x = self.get_sorted(lambda x: x.x0).x0
        y = self.get_sorted(lambda x: x.debug.y1).debug.y1

        return x, y

class Spoke:

    def __init__(self, lbls, data, orientation, val):
        """
        Store constitutive spoke and label data. 
        """
        self.orientation = orientation
        self.val = val

        if orientation == 'h':
            self.lbls = Nest(*sorted(lbls, key=lambda x: x.x0))
        else:
            self.lbls = Nest(*sorted(lbls, key=lambda x: x.y0, reverse=True))

        self.title = ', '.join([x.text.strip('\n ') for x in self.lbls])
        
        self.debug = data

        self.x0 = min([data.agg('x0', 'min'), self.lbls.agg('x0', 'min')])
        self.x1 = max([data.agg('x1', 'max'), self.lbls.agg('x1', 'max')])

        self.y0 = min([data.agg('y0', 'min'), self.lbls.agg('y0', 'min')])
        self.y1 = max([data.agg('y1', 'max'), self.lbls.agg('y1', 'max')])

    def __repr__(self):
        return f'{self.title}: {self.val} ({self.orientation})'