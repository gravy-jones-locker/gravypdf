from itertools import permutations
from pdfminer.layout import LTAnno
from .nest import Nest, Nested
import re
import statistics as stats
from . import helper
import numpy as np

class Word(Nest, Nested):

    meta_attrs = ['font']

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
    def _add_chars(self, *ad_chars, prefix=None, front=False):
        """
        Add characters to the end of a Word object with optional prefix.
        """
        if prefix is not None:
            ad_chars = [*[Char(LTAnno(x)) for x in prefix], *ad_chars]
        if not front: 
            self.extend(ad_chars)
        else:
            self[0:0] = ad_chars
        self.detail_anno()  # TODO need a way to reset font..
        self.set_font()
    
    def _combine(self, *ad_fields, delim: str=None) -> None:
        """Create a composite from the additional fields and any delimiters""" 
        for ad_field in ad_fields:
            if delim is not None:
                delim = helper.get_delim(self.text, ad_field.text, delim)
            self._add_chars(*ad_field, prefix=delim) 

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

        """  # Doesn't work for some reason..
        i = self.text.find(char_str)
        ref_str = ''
        j = 0
        while i + j < len(self):
            char = self[i+j]
            ref_str += char.text
            if ref_str == char_str:
                break
            j += 1
        return self[i:i+j]
        """

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
    
    @Nest.Decorators.rehome
    def rm_bad_chars(self):
        """
        Remove 'bad' characters.
        """
        i = 0
        while i < len(self):
            char = self[i]
            if char.text not in ['\xa0']:
                yield char
            else:
                while not self[i+1].text.strip():
                    i += 1
                yield char
            i += 1
        
    @Nest.Decorators.rehome
    def replace_chars(self, sub: str, repl: str):
        """
        Replace the given char with the replacement char.
        """
        for i, char in enumerate(self):
            if char.text == sub:
                if i == 0 or i == len(self) - 1:
                    continue
                char = Char(LTAnno(repl))
                char.set_details(self[i-1], self[i+1])
            yield char

    def detail_anno(self):
        """
        Add positional/font/text info to all 'LTAnno' chars.
        """
        def has_x0(char):
            return char.cvttype != 'LTAnno' and hasattr(char, 'x0')

        for i, char in enumerate(self):
            if has_x0(char):
                continue
            prev_chars = self[:i].filter(has_x0)
            next_chars = self[i+1:].filter(has_x0)
            if not prev_chars:
                prev_char = next_chars[0]
            else:
                prev_char = prev_chars[-1]
            if not next_chars:
                next_char = prev_char
            else:
                next_char = next_chars[0]
            char.set_details(prev_char, next_char)
        return self
    
    def get_text(self):
        return ''.join([x.text for x in self])   

    def split_word(self, delim, rm_blanks=False, ignore_pars=False, max_parts=None,
    start=None):
        """
        Split the word given a certain delimiter.
        """
        i = 0
        count = 0
        parts = self.text.split(delim)
        part = ''
        while i < len(parts):
            if start is not None and i <= start:
                part += delim + parts[i] if part != '' else parts[i]
                i += 1
                continue
            elif start is None:
                part = parts[i]
            if ignore_pars and '(' in part and ')' not in part:
                if start is not None:
                    i -= 1
                for j, ad_part in enumerate(parts[i+1:], start=1):
                    if ')' in ad_part:
                        part = part + delim + delim.join(parts[i+1:i+j+1])
                        i += j
                        break
                if start is not None:
                    i += 1
            if not rm_blanks or part not in [' ', delim, '']:
                if part.strip():
                    yield self.extract_chars(part)
                part = ''
                count += 1
            if max_parts and count == max_parts - 1 and i < len(parts):
                if ''.join(parts[i:]).strip():
                    yield self.extract_chars(delim.join(parts[i:])) 
                return
            i += 1

    def set_font(self):
        """
        Find and return the most common font/size in the word.
        """        
        fonts = [f'{x.caps}{x.font}' for x in self if hasattr(x, 'fontname') and x.text.strip()]
        sel = set(fonts)
        if len(sel) == 1:
            self.font = str(sel).strip('{}\'')
            return self

        count = [(y, len([x for x in fonts if x == y])) for y in sel]
        count.sort(key=lambda x: x[1], reverse=True)

        self.font = count[0][0]
        return self

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
    
    @property
    def firstchar(self):
        for char in self:
            if char.text.isalnum():
                return char
        return self[0]  # Copout in case none was found

class Words(Word, Nested):

    def clean(self):
        """
        Clean wspace and interpolate position values for 'LTAnno' chars.
        """
        self = self.filter(Word.has_txt).split_spaces()
        
        self.apply_nested(Word.rm_wspace)   # Get rid of leading/trailing wspace
        self.apply_nested(Word.detail_anno) # Detail position/text of 'LTAnno'
        self.apply_nested(Word.rm_double_spaced)
        self.apply_nested(Word.rm_bad_chars)
        self.apply_nested(Word.set_font)
        self.replace_spaces()

        # After changes calculate new positional info of each word
        self.apply_nested(Nest.set_bbox)

        return self

    def replace_spaces(self):
        """
        Replace suspicious space characters with normal spaces.
        """
        count_spaces = self.text.count(' ')
        for sub in ['\t']:
            if self.text.count(sub) > count_spaces:
                self.apply_nested(Word.replace_chars, sub, ' ')
        pass
    
    @Nest.Decorators.rehome
    def split_close(self):
        """
        Split any words which have large gaps between them.
        """
        i = 0
        while i < len(self):
            word = self[i]
            avg_w = stats.median([x.w for x in word])
            j = 5  # Start midway through the word
            offset = 0
            while j < len(word) - 1:
                char = word[j]
                if not char.text.strip():
                    if char.w > 1.5 * avg_w:
                        part = word[offset:j]
                        if part.text.strip():
                            yield part
                        offset = j + 1
                j += 1
            word = word[offset:]
            if word:
                yield word
            i += 1

    @Nest.Decorators.rehome
    def join_bullets(self, curves):
        """
        Wherever there are isolated bullets prepend them to the next word.
        """
        i = 0
        while i < len(self):
            word = self[i]
            if i != len(self) - 1 and word.text.strip() in helper.BULLETS:
                if abs(word.midy - self[i+1].midy) < 6:
                    word._combine(self[i+1], delim=' ')
                else:
                    word = self[i+1] 
                i += 1
            else:
                for curve in curves:
                    if abs(curve.midy-word.midy)<5 and 0< word.x0-curve.x1<10:
                        word._add_chars(prefix='• ', front=True)
                        break
            yield word
            i += 1

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
        p_str = r'(?:page|p|^|seite)\.{0,1}\s{0,1}\d+'
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
    
    def is_raligned(self):
        diff_l = sum([abs(x.x0-y.x0) for (x, y) in permutations(self, r=2)])
        diff_r = sum([abs(x.x1-y.x1) for (x, y) in permutations(self, r=2)])
        return diff_l > diff_r
    
    @Nest.Decorators.rehome
    def sort_margin_notes(self, margin, tol):
        """
        Arrange notes to the left of the given margin to be contiguous.
        """
        i = 0
        while i < len(self):
            word = self[i]
            if word is not None:
                if word.x0 + tol > margin:
                    yield word 
                else:
                    for j, ad_word in enumerate(self[i+1:]):
                        if word.y0 - ad_word.y1 > 10:
                            yield word
                            break
                        if ad_word.x0 + tol > margin:
                            continue
                        word._combine(ad_word, delim=' ')
                        yield word
                        self[j] = None
                        break
            i += 1

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