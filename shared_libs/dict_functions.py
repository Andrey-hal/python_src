class Map(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Recursively turn nested dicts into DotDicts
        for key, value in self.items():
            if type(value) is dict:
                self[key] = Map(value)

    def __setitem__(self, key, item):
        if type(item) is dict:
            item = Map(item)
        super().__setitem__(key, item)

    __setattr__ = __setitem__
    __getattr__ = dict.__getitem__