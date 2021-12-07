from forgot_again.file import load_ast_if_exists, pprint_to_file


class SecondaryParams:
    def __init__(self, required, file_name=''):
        self._required = required
        self._params = None
        self.file_name = file_name

    @property
    def params(self):
        if self._params is None:
            self._params = {
                k: v[1]['value'] for k, v in self._required.items()
            }
        return self._params

    @params.setter
    def params(self, d):
        self._params = d

    @property
    def required(self):
        return dict(**self._required)

    def load_from_config(self):
        self.params = load_ast_if_exists(self.file_name, default=self.params)

    def save_config(self):
        pprint_to_file(self.file_name, self._params)
