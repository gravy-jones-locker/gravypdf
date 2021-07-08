from .nest import Nest, Nested
import re
import statistics as stats
from . import helper

class Word(Nest, Nested):

    def lookup(self, lookup_strs):
        """
        Return True/False indication of whether string was found
        """
        for lookup in lookup_strs:
            if not re.search(lookup, self.text):
                continue

            return True  # True if matching string found

    def find_str(self, ref, case_sensitive=False):
        """
        Returns indication if ref string found in text.
        """
        if not case_sensitive:
            return re.findall(ref, self.text.lower())
        return re.findall(ref, self.text)

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

        delims = re.findall(r'(cid:\S+)', self.text[:i])
        i -= len(delims) * 6

        new = self[i:i+len(char_str)]

        #self = Word(*self[:i], *self[i+len(char_str):])

        return new

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

    def detail_anno(self):
        """
        Add positional/font/text info to all 'LTAnno' chars.
        """
        for i, char in enumerate(self):
            if char.cvttype != 'LTAnno':
                continue

            prev_char, next_char = self[i-1], self[i+1]
            char.set_details(prev_char, next_char)
        return self
    
    def get_text(self):
        return ''.join([x.text for x in self])   

    @helper.lazy_property
    def font(self):
        """
        Find and return the most common font/size in the word.
        """        
        fonts = [f'{x.caps}{x.font}' for x in self]
        sel = set(fonts)
        if len(sel) == 1:
            self._font = str(sel).strip('{}\'')

        count = [(y, len([x for x in fonts if x == y])) for y in sel]
        count.sort(key=lambda x: x[1], reverse=True)

        self._font = count[0][0]

class Words(Word, Nested):

    def clean(self):
        """
        Clean wspace and interpolate position values for 'LTAnno' chars.
        """
        self = self.filter(Word.has_txt).split_spaces()
        
        self.apply_nested(Word.rm_wspace)   # Get rid of leading/trailing wspace
        self.apply_nested(Word.detail_anno) # Detail position/text of 'LTAnno'

        # After changes calculate new positional info of each word
        self.apply_nested(Nest.set_bbox)

        return self

    @Nest.Decorators.rehome
    def split_fonts(self):
        """
        Split anything grouped together which has a different font.
        """
        testC = lambda x: x.isascii() and (x.isdigit() or x.isalpha())
        for word in self:
            if len(set([x.font for x in word])) == 1:
                yield word
                continue

            font_changes = [0]
            ref_i = None
            for i in range(1, len(word)):
                if not testC(word[i].text):
                    continue
                if ref_i == None:
                    ref_i = i
                    continue
                curr_f = word[i].font
                prev_f = word[ref_i].font
                if i - font_changes[-1] > 6 and curr_f != prev_f:
                    font_changes.append(i)
                ref_i = i

            if len(font_changes) == 1:
                yield word
                continue

            rem = word
            for i in font_changes[1:]:
                sel, rem = rem.split(lambda x: x.i <= i-1)
                if sel:
                    sel.set_bbox()
                    yield sel
            if rem:
                rem.set_bbox()
                yield rem

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

    @Nest.Decorators.rehome
    def split_spaces(self):
        """
        Split given distribution of whitespace.
        """
        for word in self:
            if '    ' not in word.text:
                yield word
            else:
                parts = re.split(r'[\s\|,·]{4,200}', word.text)
                for part in [x for x in parts if x]:
                    new = word.extract_chars(part)
                    new.set_bbox()
                    yield new

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

class Char(Nested):

    def is_wspace(self):
        """
        Return True if the character is a whitespace/newline character.
        """
        return self.text.isspace() or self.text == '\n' or self.cvttype == 'LTAnno'

    def set_details(self, prev_char, next_char):
        """
        Retrieve positional/text/font details from surrounding chars.
        """        
        self.x0, self.x1 = prev_char.x1, next_char.x0
        self.y0, self.y1 = prev_char.y0, prev_char.y1

        self.fontname = prev_char.fontname
        return self

    @helper.lazy_property
    def font(self):
        if '+' in self.fontname:
            fname = ''.join(self.fontname.split('+')[1:])
        else:
            fname = self.fontname

        self._font = f'{fname}_{helper.round_two(self.h)}'

    @helper.lazy_property
    def caps(self):
        self._caps = 'CAPS' if self.text.isupper() else ''

Words.nested = Word  # Forward declaration workaround
Word.nested  = Char