class Settings(dict):

    defaults = {}

    fallbacks = {}

    def __init__(self, user_settings):
        """
        Combine default and user setting tables.
        """
        for k in [k for k in user_settings if k not in self.defaults]:
            raise ValueError(f'Unrecognized setting: {k}')

        # combine with user dict in 2nd place to override defaults
        self.combi = {**self.defaults, **user_settings}

        self.populate_fallbacks()

        super().__init__(**self.combi)

    def populate_fallbacks(self):
        """
        Fill blank entries in the combined dictionary with fallbacks.
        """
        for k in [k for k in self.fallbacks if not self.combi[k]]:
            new_k = self.fallbacks[k]

            self.combi[k] = self.defaults[new_k] 