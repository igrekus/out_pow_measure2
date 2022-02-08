from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant


class MeasureModel(QAbstractTableModel):
    def __init__(self, parent=None, header=None):
        super().__init__(parent)

        self._header = header or ['#']
        self._data = list()

    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

    def update(self, point: dict):
        self.beginResetModel()
        try:
            idx = self._data[-1]['idx'] + 1
        except LookupError:
            idx = 1
        self._data.append({'idx': idx, **point})
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
        return len(self._data)

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self._header)

    def data(self, index, role=None):
        if not index.isValid():
            return QVariant()
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole:
            row_data = self._data[row]
            if col == 0:
                return QVariant(row_data['idx'])
            elif col == 1:
                return QVariant(row_data['f'] / 1_000_000_000)
            elif col == 2:
                return QVariant(row_data['p'])
            elif col == 3:
                return QVariant(row_data['read_pow'])
            elif col == 4:
                return QVariant(row_data['adjusted_pow'])
            else:
                QVariant()
        return QVariant()

    def calData(self):
        return list(self._data)

    def is_ready(self):
        return bool(self._data)
