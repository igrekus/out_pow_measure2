from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QHeaderView
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from measuremodel import MeasureModel
from mytools.backgroundworker import BackgroundWorker, CancelToken, TaskResult
from instrumentcontroller import InstrumentController


class PulseModeWidget(QWidget):

    _measureFinished = pyqtSignal(TaskResult)

    def __init__(self, parent=None, controller: InstrumentController=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_QuitOnClose)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # create instance variables
        self._ui = uic.loadUi('pulsemodewidget.ui', self)

        self._worker = BackgroundWorker(self)
        self._token = CancelToken()

        self._controller = controller

        self._task = list()
        self._model = MeasureModel(parent=self, header=['№', 'Fвх, ГГц', 'Pвх, дБм', 'Pвх.изм, дБм', 'ΔPвх, дБм'])

        self._connectSignals()
        self._initUi()

    def _connectSignals(self):
        self._measureFinished.connect(self.on_measure_finished, type=Qt.QueuedConnection)

    def _initUi(self):
        self._ui.tableMeasure.setModel(self._model)
        self._ui.tableMeasure.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    # worker dispatch
    def _startWorker(self, fn, cb, **kwargs):
        self._worker.runTask(fn=fn, fn_finished=cb, **kwargs)

    def _measure(self):
        if not self._task:
            return
        self._token = CancelToken()
        self._startWorker(
            fn=self._controller.measure,
            cb=self._measureFinishedCallback,
            report_fn=self._measureInProgress,
            params=self._controller.secondaryParams,
            token=self._token,
            task=self._task
        )

    # callbacks
    def _measureFinishedCallback(self, result: tuple):
        self._measureFinished.emit(TaskResult(*result))

    def _measureInProgress(self, data):
        print('measure in progress', data)

    @pyqtSlot(TaskResult)
    def on_measure_finished(self, result):
        ok, msg = result.values
        if not ok:
            print(f'error during raw command: {msg}')
            # QMessageBox.information(self, 'Внимание', 'Контроллер GRBL не найден, проверьте подключение.')
            return
        print('measure result', ok, msg)

    @pyqtSlot(list)
    def on_calTask_ready(self, task):
        print('task ready', task)
        self._task = task

    @pyqtSlot()
    def on_btnMeasure_clicked(self):
        self._measure()
