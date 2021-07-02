from .nest import Nest, Nested
import re
import statistics as stats
from . import helper

class Words(Nest, Nested):

    def score_incidence(self, lookup_strs, consecutive=False):
        """
        Score the number of times the lookup strings were found.
        """
        hits = []
        for word in self:
            hit = word.lookup(lookup_strs)
            hits.append(hit)

        if consecutive:
            hits = helper.filter_consecutive(hits)

        return len([x for x in hits if x])

    def shares_header(self, header):
        """
        Check whether the header structure is (roughly) matched.
        """
        return len(self) > 3  # TODO improve this..

    def get_text(self):
        return ' '.join([x.text for x in self])

class Header(Words):

    def __init__(self, row, pattern):
        """
        Take everything from the row and store a filtered Nest of known labels.
        """
        helper.store_attrs(self, row)
        
        self.pattern = pattern
        
        self.lbls = self.filter(Word.lookup, self.pattern)
        
        self.lbls.sort(key=lambda x:x.x0)
        self.lbls.reset_idx()

    def cvt_header2tbl(self, prev_header, rows):
        """
        Complete info from surroundings and return table.
        """
        for lo in rows[prev_header.i+1:self.i]:
            if lo.shares_header(self):
                break  # Work way up from prev to find table end

        for hi in rows[self.i+1:]:
            if hi.agg('x0', 'min') <= self.agg('x0', 'min'):
                title = hi.text
                break
            elif hi.i == len(rows) - 1:
                title = 'n/a'

        return self, lo, title

    @helper.lazy_property
    def period(self):
        fn = lambda x, y: abs(x.x0 - y.x0)
        self._period = stats.median([x for x in self.lbls.get_delta(fn)])
            
class Word(Nest, Nested):

    def lookup(self, lookup_strs):
        """
        Return True/False indication of whether string was found
        """
        for lookup in lookup_strs:
            if not re.search(lookup, self.text):
                continue

            return True  # True if matching string found

    def has_txt(self):
        """
        Checks whether the subsidiary characters are empty or not.
        """
        return not all([x.is_wspace() for x in self])

    def extract_chars(self, char_str):
        """
        Remove and return the specified characters from the Word instance.
        """
        i = self.text.find(char_str)
        new = self[i:i+len(char_str)]

        self = Word(*self[:i], *self[i+len(char_str):])

        return new

    @Nest.Decorators.set_bbox
    def rm_wspace(self):
        """
        Remove any surrounding whitespace.
        """
        for st_i, st_char in enumerate(self):
            if st_char.is_wspace():
                continue
            
            for end_i, end_char in enumerate(reversed(self[st_i:])):
                if end_char.is_wspace():
                    continue

                return self[st_i:-end_i] if end_i > 0 else self[st_i:]

    def get_text(self):
        return ''.join([x.text for x in self])   

    @property
    def font(self):
        """
        Find and return the most common font/size in the word.
        """
        fonts = [f'{x.fontname}_{round(x.h, 0)}' for x in self]
        sel = set(fonts)
        if len(sel) == 1:
            return str(sel).strip('{}\'')

        count = [(y, len([x for x in fonts if x == y])) for y in sel]
        count.sort(key=lambda x: x[1], reverse=True)
        
        return count[0][0]

class Char(Nested):

    def is_wspace(self):
        """
        Return True if the character is a whitespace/newline character.
        """
        return self.text.isspace() or self.text == '\n'

Words.nested = Word  # Forward declaration workaround
Word.nested  = Char