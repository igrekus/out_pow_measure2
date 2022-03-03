import datetime
import os

from collections import defaultdict
from subprocess import Popen

from pandas import DataFrame
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant

from forgot_again.file import make_dirs
from instr.const import GIGA


class PulseMeasurePowModel(QAbstractTableModel):
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
        # a = {'f': 2700000000, 'p': 14.9917657, 'read_pow': 12.7655025, 'adjusted_pow': 15.0660151}
        self.beginResetModel()

        p = round(point['p'])
        p_ref = point['p_ref']
        f = round(point['f'] / GIGA, 3)
        self._pows = sorted(set(self._pows + [p_ref]))
        self._freqs = sorted(set(self._freqs + [f]))
        self._data[p_ref][f] = (point['read_pow'], point['adjusted_pow'])

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
            return QVariant(self._data[p].get(self._freqs[col - 1], (0, 0))[1])

        return QVariant()

    def is_ready(self):
        return bool(self._data)

    def export(self, suffix=''):
        device = f'{suffix}' if suffix else ''
        path = 'xlsx'
        make_dirs('xlsx')
        file_name = f'./{path}/{device}-{datetime.datetime.now().isoformat().replace(":", ".")}.xlsx'

        pows = sorted(self._data.keys())
        vals = [{f'Fвх={k}, ГГц': v[1] for k, v in row.items()} for row in self._data.values()]
        vals = [{'Pвх, дБм': p, **v} for p, v in zip(pows, vals)]

        df = DataFrame(vals)
        df.to_excel(file_name, index=False)

        full_path = os.path.abspath(file_name)
        Popen(f'explorer /select,"{full_path}"')
