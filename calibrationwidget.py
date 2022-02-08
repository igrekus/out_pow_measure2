from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from calinmodel import CaliModel
from mytools.backgroundworker import BackgroundWorker, CancelToken, TaskResult
from instrumentcontroller import InstrumentController


class CalibrationWidget(QWidget):

    _calibrateInFinished = pyqtSignal(TaskResult)
    _calibrateOutFinished = pyqtSignal(TaskResult)
    _calibrateInReport = pyqtSignal(dict)
    _calibrateOutReport = pyqtSignal(dict)

    def __init__(self, parent=None, controller: InstrumentController=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_QuitOnClose)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # create instance variables
        self._ui = uic.loadUi('calibrationwidget.ui', self)

        self._worker = BackgroundWorker(self)
        self._token = CancelToken()

        self._controller = controller

        self._cal_in_model = CaliModel(parent=self, header=['№', 'Fвх, ГГц', 'Pвх, дБм', 'Pвх.изм, дБм', 'ΔPвх, дБм'])
        self._cal_out_model = CaliModel(parent=self, header=['№', 'Fвх, ГГц', 'Pвх, дБм', 'Pвх.изм, дБм', 'ΔPвх, дБм'])

        self._connectSignals()
        self._initUi()

    def _connectSignals(self):
        self._calibrateInFinished.connect(self.on_calibrateIn_finished, type=Qt.QueuedConnection)
        self._calibrateOutFinished.connect(self.on_calibrateOut_finished, type=Qt.QueuedConnection)
        self._calibrateInReport.connect(self.on_calibrateInReport, type=Qt.QueuedConnection)
        self._calibrateOutReport.connect(self.on_calibrateOutReport, type=Qt.QueuedConnection)

    def _initUi(self):
        self._ui.tableCalibrateIn.setModel(self._cal_in_model)
        self._ui.tableCalibrateIn.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self._ui.tableCalibrateOut.setModel(self._cal_out_model)
        self._ui.tableCalibrateOut.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    # worker dispatch
    def _startWorker(self, fn, cb, **kwargs):
        self._worker.runTask(fn=fn, fn_finished=cb, **kwargs)

    def _calibrateIn(self):
        self._cal_in_model.clear()
        self._token = CancelToken()
        self._startWorker(
            fn=self._controller.calibrateIn,
            cb=self._calibrateInFinishedCallback,
            report_fn=self._calibrateInProgress,
            params=self._controller.secondaryParams,
            token=self._token,
        )

    def _calibrateOut(self):
        res = QMessageBox.question(self, 'Внимание!', 'Подключите выходной тракт!')
        if res != QMessageBox.Yes:
            return

        self._cal_out_model.clear()
        self._token = CancelToken()
        self._startWorker(
            fn=self._controller.calibrateOut,
            cb=self._calibrateOutFinishedCallback,
            report_fn=self._calibrateOutProgress,
            params=self._controller.secondaryParams,
            token=self._token,
        )

    # callbacks
    def _calibrateInFinishedCallback(self, result: tuple):
        self._calibrateInFinished.emit(TaskResult(*result))

    def _calibrateOutFinishedCallback(self, result: tuple):
        self._calibrateOutFinished.emit(TaskResult(*result))

    def _calibrateInProgress(self, data):
        self._calibrateInReport.emit(data)

    def _calibrateOutProgress(self, data):
        self._calibrateOutReport.emit(data)

    @pyqtSlot(TaskResult)
    def on_calibrateOut_finished(self, result):
        ok, msg = result.values
        if not ok:
            print(f'error during raw command: {msg}')
            # QMessageBox.information(self, 'Внимание', 'Контроллер GRBL не найден, проверьте подключение.')
            return
        print('cal in result', ok, msg)

    @pyqtSlot(TaskResult)
    def on_calibrateIn_finished(self, result: TaskResult):
        ok, msg = result.values
        if not ok:
            print(f'error during ask command, check logs: {msg}')
            # QMessageBox.information(self, 'Внимание', 'Ошибка выполнения запроса к GRBL, подробности в логах.')
            return
        print('cal out result', ok, msg)

    @pyqtSlot(dict)
    def on_calibrateInReport(self, data):
        print('calibrate in point:', data)
        self._cal_in_model.update(data)

    @pyqtSlot(dict)
    def on_calibrateOutReport(self, data):
        print('calibrate in point:', data)
        self._cal_out_model.update(data)

    @pyqtSlot()
    def on_btnCalibrateIn_clicked(self):
        self._calibrateIn()

    @pyqtSlot()
    def on_btnCalibrateOut_clicked(self):
        self._calibrateOut()
