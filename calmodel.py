from collections import defaultdict

from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant
from forgot_again.file import pprint_to_file, load_ast_if_exists

from instr.const import GIGA


class CaliModel(QAbstractTableModel):
    def __init__(self, parent=None, header=None):
        super().__init__(parent)

        self._header = header or ['#']
        self._data = defaultdict(dict)
        self._pows = list()
        self._freqs = list()

    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self._pows.clear()
        self._freqs.clear()
        self.endResetModel()

    def update(self, point: dict):
        self.beginResetModel()

        p = round(point['p'])
        f = round(point['f'] / GIGA, 3)
        self._pows = sorted(set(self._pows + [p]))
        self._freqs = sorted(set(self._freqs + [f]))
        self._data[p][f] = (point['read_pow'], point['delta'])

        self._header = ['Pвх, дБм'] + [f'Fвх={v}, ГГц' for v in self._freqs]

        self.endResetModel()

    def headerData(self, section, orientation, role=None):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section < len(self._header):
                    return QVariant(self._header[section])
        return QVariant()

    def rowCount(self, parent=None, *args, **kwargs):
        if parent.isValid():
            return 0
        return len(self._pows)

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self._header)

    def data(self, index, role=None):
        if not index.isValid():
            return QVariant()
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole:
            p = self._pows[row]
            if col == 0:
                return QVariant(p)
            return QVariant(self._data[p].get(self._freqs[col - 1], (0, 0))[0])
        return QVariant()

    def calData(self):
        out = list()
        for p in self._pows:
            for f in self._freqs:
                out.append({
                    'p': p,
                    'f': f,
                    'read_pow': self._data[p][f][0],
                    'delta': self._data[p][f][1],
                })
        return out

    def is_ready(self):
        return bool(self._data)

    def saveCalData(self, file):
        pprint_to_file(file, dict(self._data.items()))

    def loadCalData(self, file):
        res: dict = load_ast_if_exists(file, {})
        self._pows = sorted(res.keys())
        self._freqs = sorted(list(res.values())[0].keys())

        self.beginResetModel()
        self._header = ['Pвх, дБм'] + [f'Fвх={v}, ГГц' for v in self._freqs]
        self._data = res
        self.endResetModel()
