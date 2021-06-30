import itertools
import re
import numpy as np
from . import helper
from collections.abc import MutableSequence

class BasePDF:
    @property
    def midx(self):
        return (self.x1 + self.x0) / 2

    @property
    def midy(self):
        return (self.y1 + self.y0) / 2

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def orientation(self):
        if self.y1 - self.y0 > self.x1 - self.x0:
            return 'v'
        else:
            return 'h'

class Nest(MutableSequence, BasePDF):

    """
    Text/edges and other sub (pdfminer) elements are grouped into Nests. These
    behave like mutable sequences, with additional functions/attributes.
    """

    class Decorators:

        @classmethod
        def set_bbox(decs, func):
            """
            Resets coordinates of nest based on (new) elements.
            """
            def inner(cls, *args, **kwargs):
                cls = func(cls, *args, **kwargs)
                cls.set_bbox()
                return cls            
            return inner

        @classmethod
        def rehome(decs, func):
            """
            Simplifies functions which synthesise new nests from existing items.
            """
            @decs.set_bbox
            def inner(cls, *args, **kwargs):
                out = type(cls)()
                for elem in func(cls, *args, **kwargs):
                    out.addtwigs(elem)
                return out
            return inner

    def __init__(self, *elems, **kwargs):
        """
        Compile an iterable into a nest for the first time.
        """        
        self._ls = []
        for i, elem in enumerate(elems):
            if kwargs.get('cast'):
            
                if helper.chk_sys_it(elem):
                    elem = type(self)(*elem, **kwargs)  
                elif not isinstance(elem, self.nested):
                    elem = self.nested(elem)

            self.addtwigs(elem)
        
        self.set_bbox()

    ####  apply builtins to inner (_ls) list of nested items  ####

    def __len__(self):
        return len(self._ls)

    def __delitem__(self, index):
        self._ls.__delitem__(index)

    def insert(self, index, value):
        self._ls.insert(index, value)

    def __setitem__(self, index, value):
        self._ls.__setitem__(index, value)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self.copy(_ls=self._ls[index])
        return self._ls.__getitem__(index)

    def __iter__(self):
        for obj in self._ls:
            yield obj

    def sort(self, **kwargs):
        self._ls = sorted(self._ls, **kwargs)

    def copy(self, **kwargs):
        """
        Combine stored attrs and modifications in kwargs for new nest.
        """
        out = type(self)()
        for attr in ['parent', 'i', '_ls']:
            v = kwargs[attr] if attr in kwargs else getattr(self, attr, None)
            setattr(out, attr, v)
        return out

    def addtwigs(self, *elems):
        """
        Append new element to sequence and assign index as default.
        """
        for elem in elems:
            elem.i = len(self)
            self._ls.append(elem)

    def reset_idx(self):
        """
        Reset element indices to reflect current order in Nest.
        """
        for i, elem in enumerate(self):
            elem.i = i

    def agg(self, attr, qnt='median'):
        """
        Returns specified statistical quantity of the specified attribute.
        """
        ref_ls = [getattr(x, attr) for x in self if hasattr(x, attr)]
        if not ref_ls:
            return None        
        return eval(f'np.{qnt}')(ref_ls)

    def set_bbox(self, x_only=False, y_only=False):
        """
        Aggregate object coordinates to get new bounding box.
        """
        if not y_only:
            self.x0 = self.agg('x0', 'min')
            self.x1 = self.agg('x1', 'max')

        if not x_only:
            self.y0 = self.agg('y0', 'min')
            self.y1 = self.agg('y1', 'max')

        return self

    def approximate(self, attr, v):
        """
        Return the element with the closest value.
        """
        min_dist = min([abs(v - getattr(x, attr, '')) for x in self])

        return [x for x in self if abs(v - getattr(x, attr, '')) == min_dist][0]

    @Decorators.rehome
    def cluster(self, fn, inv=False):
        """
        Group nested elements by the attribute and function specified.
        """
        ref_ls = []  # Build list of points separated by tolerance
        
        for elem in self:
            if not any([fn(elem, x) for x in ref_ls]):
                ref_ls.append(elem)

        for ref in ref_ls:
            cluster_ls = [x for x in self if fn(ref, x) or x == ref]
            
            yield type(self)(*cluster_ls)

    @Decorators.rehome
    def combine(self):
        """
        Combine Nested elements into one instance.
        """
        for sub_elem in [x for y in self for x in y]:
            yield sub_elem        

    @Decorators.rehome
    def negative_cluster(self, y_gap, x_gap):
        """
        Cluster items which do not have the specified gap between them.
        """
        def chkGap(x, y):
            chk_y = abs(x.y1-y.y0) < y_gap or x.y1 > y.y0 if y_gap else True
            chk_x = abs(x.x0-y.x0) < x_gap if x_gap else True
            return chk_y and chk_x

        self.sort(key=lambda x:x.y1, reverse=True)
        ls = self._ls
        while ls:
            cluster_ls = Nest(ls.pop(0))
            new = []
            for elem in ls:
                if not chkGap(elem, cluster_ls):
                    new.append(elem)
                    continue
                cluster_ls.addtwigs(elem)
                cluster_ls.set_bbox()
            yield type(self)(*cluster_ls)    
            ls = new       

    @Decorators.rehome
    def denest(self, attr='__len__', flatten=False, cast=False):
        """
        Expose all nested elements according to function specified.
        """
        for elem in self:
            
            if hasattr(elem, attr):
                sub = elem if attr == '__len__' else getattr(elem, attr)
                yield from type(self)(*sub, cast=cast).denest(attr, cast=cast)        
            
            if not hasattr(elem, attr) or not flatten:
                yield elem

    @Decorators.rehome
    def filter(self, fn=None, *args, **kwargs):
        """
        Return a filtered nest according to the keys/values in the mapping.
        """
        for elem in self:
            if fn and not fn(elem, *args, **kwargs):
                continue
        
            yield elem

    @Decorators.rehome
    def filter_attrs(self, **filters):
        """
        Specify key/value pairs by which to filter the nest and pass to filter.
        """
        for elem in self:
            if not all([getattr(elem, k, '') == v for k, v in filters.items()]):
                continue

            yield elem

    @Decorators.rehome
    def slot_y(self, slots):
        """
        Slot the members of the nest into the slots specified.
        """
        slots.sort(key=lambda x:x[0])

        for i, (slot_y0, slot_y1) in enumerate(slots):

            filling = self.slice(y0=slot_y0, y1=slot_y1)
            
            if filling:  # Yield filling individually but snapped to fill gap
                filling[0].y0  = slot_y0
                filling[-1].y1 = slot_y1
                
                yield from filling

    @Decorators.rehome
    def snap(self, template, fn):
        """
        Snap the nested elements to the template - multiplying/duplicating as 
        necessary.
        """
        for elem in template:
            matches = self.filter(Nested.chk_intersection, elem, y_only=True)
            if len(matches) == 1:
                yield matches[0]
            
            else:
                dists = [abs(fn(elem, x)) for x in matches]
                
                closest = [i for i, x in enumerate(dists) if x == min(dists)][0]
                yield matches[closest]

    def fill_y_gaps(self, lim_y0, lim_y1):
        """
        Fill any gaps between the y coordinates of the nested elements.
        """
        self.sort(key=lambda x:x.y0)

        # if top row right next to header then fill everything down
        # otherwise assume centre align and spread evenly by height

        topalign = False  # Will be aggregate of spacing vs row heights

        for i, elem in enumerate(self):
            elem_midy = int(elem.midy)  # Need static midpoint
            elem.y0 = self[i-1].y1 + 1 if i != 0 else lim_y0
            if topalign:
                continue  # True if only filling down required
            if i == len(self) - 1:
                elem.y1 = lim_y1
                continue  # True if currently on highest element

            y1_ext = elem_midy + (elem_midy - elem.y0)
            next_y = self[i+1].y0 - elem.h / 2  #TODO improve padding  # The next available element

            y1 = y1_ext if y1_ext < next_y else next_y
            elem.y1 = y1

    def slice(self, x0=None, x1=None, y0=None, y1=None):
        """
        Take a positional slice of elements from the cluster.
        """
        x0 = x0 if x0 else self.x0 - 1  # Offset includes self if not specified
        x1 = x1 if x1 else self.x1 + 1

        y0 = y0 if y0 else self.y0 - 1
        y1 = y1 if y1 else self.y1 + 1
        
        chkHoriz = lambda x: x.x0 > x0 and x.x1 < x1
        chkVert = lambda x: x.y0 > y0 and x.y1 < y1

        return self.filter(lambda x: chkHoriz(x) and chkVert(x))

    def split(self, fn=None, *args, **filters):
        """
        Apply filter and return *two* nests: true results, false results.
        """
        out_i  = self.filter(fn, *args, **filters)
        out_ii = self.copy(_ls=[x for x in self if x not in out_i])

        return out_i, out_ii

    def get_delta(self, fn, inv=False):
        """
        Return the result of the function passed when applied to consecutive
        elements in order (as a list of values/elements).
        """
        out = []
        for i, elem in enumerate(self):
            if (i == len(self) - 1 and not inv) or (i == 0 and inv):
                continue  # True if no elements left to compare
            i_ref = i - 1 if inv else i + 1
            out.append(fn(elem, self[i_ref]))
        return out

    def mega_cluster(self, orientation, tol):
        """
        Apply multiple clustering strategies to accommodate alignments.
        """
        if orientation == 'horizontal':
            vars = ['x.x0', 'x.x1', 'x.midx']
        else:
            vars = ['x.y0', 'x.y1', 'x.midy']

        out = type(self)()
        max_len = 0
        for var in vars:
            clusters = self.cluster(lambda x: eval(var), tol)
            
            # Check to see if any match the highest count
            for cluster in clusters:
                if len(cluster) <= max_len:
                    continue
                max_len = len(cluster)
                align = var[2:]

            out.addtwigs(clusters)

        return out, align

    def apply_nested(self, fn, *args, **kwargs):
        """
        Apply some function to all the nested elements in the nest.
        """
        for i, obj in enumerate(self):
            self[i] = fn(obj, *args, **kwargs)

    def get_sorted(self, fn, i=0, inv=False):
        """
        Get the indexed element when sorted by the specified function.
        """
        return sorted(self, key=fn, reverse=inv)[i]

class Nested(BasePDF):

    def __init__(self, elem):
        """
        Store every dictionary value as an attribute of the class instance.
        """
        helper.store_attrs(self, elem)

        if type(elem).__name__.startswith('LT'):
            setattr(self, 'cvttype', type(elem).__name__)

    def chk_intersection(self, ref, x_only=False, y_only=False):
        """
        Return True if the element is inside the coordinates passed.
        """
        if not y_only:
            if ref.x0 and self.x1 <= ref.x0 or ref.x1 and self.x0 >= ref.x1:
                return False
        
        if not x_only:
            if ref.y0 and self.y1 <= ref.y0 or ref.y1 and self.y0 >= ref.y1:
                return False

        return True

    def squash(self, axis):
        """
        Squash the coordinates along the axis specified to be equivalent.
        """
        if axis == 'x':
            self.x0, self.x1 = self.midx, self.midx
        if axis == 'y':
            self.y0, self.y1 = self.midy, self.midy
        
        return self

    @property
    def text(self):
        """
        Extract and label text where available.
        """
        if hasattr(self, '_text'):
            return self._text
        elif hasattr(self, 'get_text'):
            return self.get_text()
        else:
            return None

Nest.nested = Nested  # Forward declaration workaround