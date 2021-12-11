from PyQt5 import uic
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from mytools.backgroundworker import BackgroundWorker, CancelToken, TaskResult
from instrumentcontroller import InstrumentController


class CalibrationWidget(QWidget):

    _calibrateInFinished = pyqtSignal(TaskResult)
    _calibrateOutFinished = pyqtSignal(TaskResult)

    def __init__(self, parent=None, controller: InstrumentController=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_QuitOnClose)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # create instance variables
        self._ui = uic.loadUi('calibrationwidget.ui', self)

        self._worker = BackgroundWorker(self)
        self._token = CancelToken()

        self._controller = controller

        self._connectSignals()

    def _connectSignals(self):
        self._calibrateInFinished.connect(self.on_calibrateIn_finished, type=Qt.QueuedConnection)
        self._calibrateOutFinished.connect(self.on_calibrateOut_finished, type=Qt.QueuedConnection)

    # worker dispatch
    def _startWorker(self, fn, cb, **kwargs):
        self._worker.runTask(fn=fn, fn_finished=cb, **kwargs)

    def _calibrateIn(self):
        self._token = CancelToken()
        self._startWorker(
            fn=self._controller.calibrateIn,
            cb=self._calibrateInFinishedCallback,
            report_fn=self._calibrateInProgress,
            params=self._controller.secondaryParams,
            token=self._token,
        )

    def _calibrateOut(self):
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
        print('cal in progress', data)

    def _calibrateOutProgress(self, data):
        print('cal out progress', data)

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

    @pyqtSlot()
    def on_btnCalibrateIn_clicked(self):
        self._calibrateIn()

    @pyqtSlot()
    def on_btnCalibrateOut_clicked(self):
        self._calibrateOut()
