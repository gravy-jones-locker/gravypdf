from nest import Nest, Nested
from table import Table
import re
import helper

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

    def cvt_header2tbl(self, prev_header, page):
        """
        Complete info from surroundings and return table.
        """
        for lo in page.grid.rows[prev_header.i:self.i]:
            if lo.shares_header(self):
                break  # Work way up from prev to find table end

        for hi in page.grid.rows[self.i+1:]:
            if hi.agg('x0', 'min') <= self.agg('x0', 'min'):
                title = hi.text
                break
            elif hi.i == len(page.grid.rows) - 1:
                title = 'n/a'

        return Table(page, self.agg('y1', 'max'), lo.agg('y0', 'min'), title)

    def shares_header(self, header):
        """
        Check whether the header structure is (roughly) matched.
        """
        return len(self) > 3  # TODO improve this..

    def get_text(self):
        return ' '.join([x.text for x in self])

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

    @Nest.Decorators.set_coords
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

class Char(Nested):

    def starts_new_word(self, word):
        """
        Check whether x/y distance from previous chars suggests a new word.
        """
        pass

    def is_wspace(self):
        """
        Return True if the character is a whitespace/newline character.
        """
        return self.text.isspace() or self.text == '\n'

Words.nested = Word  # Forward declaration workaround
Word.nested  = Char