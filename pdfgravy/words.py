from pdfminer.layout import LTAnno
from .nest import Nest, Nested
import re
import statistics as stats
from . import helper
import numpy as np

class Word(Nest, Nested):

    def __str__(self):
        return self.text

    def rm_double_spaced(self):
        """
        Indicate spaced incorrectly.
        """
        if '  ' not in self.text or len(self.text.split(' ')) < 4:
            return self
        
        cnt_spaces = len([x for x in self.text.strip().split(' ') if x != ''])
        cnt_double = len(self.text.strip().split('  '))

        if cnt_double < cnt_spaces - 2:
            return self  # True if normal ratio of double/single spaces

        i = 0
        while i < len(self) - 2:
            char_i  = self[i]
            char_ii = self[i+1] 
            if char_i.text != ' ' or char_ii.text != ' ':
                i += 1
                continue
            self = Word(*self[:i], *self[i+1:])
            i += 2

        return self

    @Nest.Decorators.set_bbox
    def _add_chars(self, *ad_chars, prefix=None):
        """
        Add characters to the end of a Word object with optional prefix.
        """
        if prefix is not None:
            ad_chars = [*[Char(LTAnno(x)) for x in prefix], *ad_chars]
        self.extend(ad_chars)
        self.detail_anno()

    @property
    def subs(self):
        """
        Load a list of subsidiary words separated by spaces.
        """
        subs = Words()
        for word_str in [x for x in self.text.strip().split(' ')]:
            if word_str in ['', ' '] or not word_str:
                continue
            subs.append(self.extract_chars(word_str))
        subs.set_bbox()
        return subs

    def test_alphanum(self, allow_ls=[]):
        """
        Test whether at least part of the 'word' is alphanumeric.
        """
        return any([x.test_alphanum(allow_ls) for x in self])

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

    @Nest.Decorators.set_bbox
    def extract_chars(self, char_str):
        """
        Remove and return the specified characters from the Word instance.
        """
        i = self.text.find(char_str)

        delims = re.findall(r'(cid:\S+)', self.text[:i])
        i -= len(delims) * 6

        return self[i:i+len(char_str)]

    @Nest.Decorators.set_bbox
    def rm_wspace(self, ad_ls=[]):
        """
        Remove any surrounding whitespace.
        """        
        for st_i, st_char in enumerate(self):
            if st_char.is_wspace() or st_char.text in ad_ls:
                continue

            self.wspace_delim = str(self[:st_i].text.strip())
            
            for end_i, end_char in enumerate(reversed(self[st_i:])):
                if end_char.is_wspace() or end_char.text in ad_ls:
                    continue

                return self[st_i:-end_i] if end_i > 0 else self[st_i:]
        return self

    def detail_anno(self):
        """
        Add positional/font/text info to all 'LTAnno' chars.
        """
        for i, char in enumerate(self):
            if char.cvttype != 'LTAnno':
                continue
            prev_char = self[i-1]
            next_chars = self[i:].filter(lambda x: x.cvttype != 'LTAnno')
            if not next_chars:
                next_char = prev_char
            else:
                next_char = next_chars[0]
            char.set_details(prev_char, next_char)
        return self
    
    def get_text(self):
        return ''.join([x.text for x in self])   

    @Nest.Decorators.rehome
    def split_word(self, delim, rm_blanks=False, ignore_pars=False):
        """
        Split the word given a certain delimiter.
        """
        i = 0
        parts = self.text.split(delim)
        while i < len(parts):
            part = parts[i]
            if ignore_pars and '(' in part and ')' not in part:
                for j, ad_part in enumerate(parts[i+1:], start=1):
                    if ')' in ad_part:
                        part = part + delim + delim.join(parts[i+1:i+j+1])
                        i += j
                        break
            if not rm_blanks or part not in [' ', delim, '']:
                yield self.extract_chars(part)
            i += 1

    @helper.lazy_property
    def font(self):
        """
        Find and return the most common font/size in the word.
        """        
        fonts = [f'{x.caps}{x.font}' for x in self if hasattr(x, 'fontname')]
        sel = set(fonts)
        if len(sel) == 1:
            self._font = str(sel).strip('{}\'')

        count = [(y, len([x for x in fonts if x == y])) for y in sel]
        count.sort(key=lambda x: x[1], reverse=True)

        self._font = count[0][0]

    def is_capitalised(self, thresh=0.6):
        chars = []
        for sub in self.subs:
            if not sub[0].text.isalpha():
                continue
            chars.append(sub[0])
        uppers = len([x for x in chars if x.text.isupper()])
        if uppers >= len(chars) * thresh:
            return True
        if len(chars) == 3 and uppers >= len(chars) - 1:
            return True

    @property
    def word_cnt(self):
        return len([x for x in self.raw_txt.split(' ') if x not in ['', ' ']])

    @property
    def has_digits(self):
        return any([x.isdigit() for x in self.text])

    @property
    def has_alpha(self):
        return any([x.isalpha() for x in self.text])

    @property
    def raw_txt(self):
        return self.text.strip().lower()

    @property
    def starts_cap(self):
        return [x for x in self.text if x.isalpha()][0].isupper()

    @property
    def is_sent(self):
        return self.starts_cap and self.ends_period

    @property
    def ends_period(self):
        return self.raw_txt[-1] == '.'

class Words(Word, Nested):

    def clean(self):
        """
        Clean wspace and interpolate position values for 'LTAnno' chars.
        """
        self = self.filter(Word.has_txt).split_spaces()
        
        self.apply_nested(Word.rm_wspace)   # Get rid of leading/trailing wspace
        self.apply_nested(Word.detail_anno) # Detail position/text of 'LTAnno'
        self.apply_nested(Word.rm_double_spaced)

        # After changes calculate new positional info of each word
        self.apply_nested(Nest.set_bbox)

        return self

    @Nest.Decorators.rehome
    def split_fonts(self):
        """
        Split anything grouped together which has a different font.
        """
        for word in self:
            if len(set([x.font for x in word])) == 1:
                yield word
                continue

            font_changes = [0]
            ref_i = None
            for i in range(1, len(word)):
                if not word[i].test_alphanum():
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

            for i, split_pos in enumerate(font_changes):
                if i == len(font_changes) - 1:
                    out = word.extract_chars(word.text[split_pos:])
                else:
                    out = word.extract_chars(word.text[split_pos:font_changes[i+1]])
                if out:
                    yield out

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

    @Nest.Decorators.rehome
    def sort_by_space(self):
        """
        Return words sorted by space between them (hi --> lo).
        """
        refs = self.get_delta(lambda x, y: abs(x.midy-y.midy))
        refs = [0] + refs + [0]
        
        for i, word in enumerate(self):
            if word.x0 > 320 or len(word.text.strip()) < 3:
                word.spc = 0
            else:
                word.spc = refs[i] * refs[i+1]

        for word in sorted(self, key=lambda x:x.spc, reverse=True):
            yield word

    def shares_header(self, header):
        """
        Check whether the header structure is (roughly) matched.
        """
        return len(self) > 3  # TODO improve this..

    def get_text(self):
        return ' '.join([x.text for x in self])

    def lbl_ends(self):
        """
        Label the bottomost/page lines as end lines.
        """
        p_str = r'(?:page|p|^)\.{0,1}\s{0,1}\d+'
        s_ls = sorted(self, key=lambda x:x.y0)
        for i, word in enumerate(s_ls):
            word.p_break = i == len(s_ls) - 1
            if i > 1:
                word.marks_p = False
                word.is_end = False
            elif i == 0:
                word.is_end = True
                word.marks_p = bool(re.findall(p_str, word.text.lower()))
            elif i == 1:
                word.marks_p = False
                word.is_end = s_ls[0].marks_p 

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

    def from_str(self, str_val):
        """
        Load from string.
        """
        self.text = str_val

    def is_wspace(self):
        """
        Return True if the character is a whitespace/newline character.
        """
        return self.text.isspace() or self.text == '\n'

    def set_details(self, prev_char, next_char):
        """
        Retrieve positional/text/font details from surrounding chars.
        """        
        self.x0, self.x1 = prev_char.x1, next_char.x0
        self.y0, self.y1 = prev_char.y0, prev_char.y1

        self.fontname = prev_char.fontname
        return self

    def test_alphanum(self, allow_ls=[]):
        if self.text in allow_ls:
            return True
        if not self.text.isascii():
            return False
        if self.text.isdigit() or self.text.isalpha():
            return True
        return False

    @helper.lazy_property
    def font(self):
        if '+' in self.fontname:
            fname = ''.join(self.fontname.split('+')[1:])
        else:
            fname = self.fontname

        self._font = f'{fname}_{int(round(self.h, 0))}'

    @helper.lazy_property
    def caps(self):
        self._caps = 'U' if self.text.isupper() else 'L'

Words.nested = Word  # Forward declaration workaround
Word.nested  = Char