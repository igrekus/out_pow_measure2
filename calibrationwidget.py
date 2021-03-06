from itertools import cycle

from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QMessageBox, QHeaderView, QFileDialog
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from calmodel import CaliModel
from mytools.backgroundworker import BackgroundWorker, CancelToken, TaskResult
from instrumentcontroller import InstrumentController


class CalibrationWidget(QWidget):

    _calibrateInFinished = pyqtSignal(TaskResult)
    _calibrateOutFinished = pyqtSignal(TaskResult)
    _calibrateInReport = pyqtSignal(dict)
    _calibrateOutReport = pyqtSignal(dict)
    measureTaskReady = pyqtSignal(list)

    def __init__(self, parent=None, controller: InstrumentController=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_QuitOnClose)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # create instance variables
        self._ui = uic.loadUi('calibrationwidget.ui', self)

        self._worker = BackgroundWorker(self)
        self._tokenIn = CancelToken()
        self._tokenOut = CancelToken()

        self._controller = controller

        self._cal_in_model = CaliModel(parent=self, cal_file='default_cal_in.txt', display_fn=lambda val: val[0] + val[1])
        self._cal_out_model = CaliModel(parent=self, cal_file='default_cal_out.txt', display_fn=lambda val: val[1])

        self._connectSignals()
        self._initUi()

    def _connectSignals(self):
        self._calibrateInFinished.connect(self.on_calibrateIn_finished, type=Qt.QueuedConnection)
        self._calibrateOutFinished.connect(self.on_calibrateOut_finished, type=Qt.QueuedConnection)
        self._calibrateInReport.connect(self.on_calibrateInReport, type=Qt.QueuedConnection)
        self._calibrateOutReport.connect(self.on_calibrateOutReport, type=Qt.QueuedConnection)

    def _initUi(self):
        self._ui.tableCalibrateIn.setModel(self._cal_in_model)
        self._ui.tableCalibrateIn.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._ui.tableCalibrateOut.setModel(self._cal_out_model)
        self._ui.tableCalibrateOut.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    # worker dispatch
    def _startWorker(self, fn, cb, **kwargs):
        self._worker.runTask(fn=fn, fn_finished=cb, **kwargs)

    def _calibrateIn(self):
        self._cal_in_model.clear()
        self._tokenIn = CancelToken()
        self._startWorker(
            fn=self._controller.calibrateIn,
            cb=self._calibrateInFinishedCallback,
            report_fn=self._calibrateInProgress,
            params=self._controller.secondaryParams.params,
            token=self._tokenIn,
        )

    def _calibrateOut(self):
        res = QMessageBox.question(self, '????????????', '?????????????????? ???????????????? ???????????')
        if res != QMessageBox.Yes:
            return

        self._cal_out_model.clear()
        self._tokenOut = CancelToken()
        self._startWorker(
            fn=self._controller.calibrateOut,
            cb=self._calibrateOutFinishedCallback,
            report_fn=self._calibrateOutProgress,
            params=self._controller.secondaryParams.params,
            token=self._tokenOut,
            cal_data=self._cal_in_model.calData(),
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
    def on_calibrateIn_finished(self, result: TaskResult):
        ok, msg = result.values
        if not ok:
            print(f'error during calibrate in: {msg}')
            # QMessageBox.information(self, '????????????????', '???????????? ???????????????????? ?????????????? ?? GRBL, ?????????????????????? ?? ??????????.')
            return
        print('cal in result', ok, msg)

    @pyqtSlot(TaskResult)
    def on_calibrateOut_finished(self, result):
        ok, msg = result.values
        if not ok:
            print(f'error during calibrate out: {msg}')
            # QMessageBox.information(self, '????????????????', '???????????????????? GRBL ???? ????????????, ?????????????????? ??????????????????????.')
            return
        print('cal out result', ok, msg)
        self.measureTaskReady.emit(self.task())

    @pyqtSlot(dict)
    def on_calibrateInReport(self, data):
        print('calibrate in point:', data)
        self._cal_in_model.update(data)

    @pyqtSlot(dict)
    def on_calibrateOutReport(self, data):
        print('calibrate out point:', data)
        self._cal_out_model.update(data)

    @pyqtSlot()
    def on_btnCalibrateIn_clicked(self):
        self._calibrateIn()

    @pyqtSlot()
    def on_btnCalibrateInCancel_clicked(self):
        self._tokenIn.cancelled = True

    @pyqtSlot()
    def on_btnCalibrateOut_clicked(self):
        self._calibrateOut()

    @pyqtSlot()
    def on_btnCalibrateOutCancel_clicked(self):
        self._tokenOut.cancelled = True

    @pyqtSlot()
    def on_btnLoadIn_clicked(self):
        file, _ = QFileDialog.getOpenFileName(self, '?????????????????? ???????????????????? ???? ??????????', '.', 'Text file (*.txt)')
        if not file:
            return
        self._cal_in_model.loadCalData(file)

    @pyqtSlot()
    def on_btnSaveIn_clicked(self):
        file, _ = QFileDialog.getSaveFileName(self, '?????????????????? ???????????????????? ???? ??????????', '.', 'Text file (*.txt)')
        if not file:
            return
        self._cal_in_model.saveCalData(file)

    @pyqtSlot()
    def on_btnLoadOut_clicked(self):
        file, _ = QFileDialog.getOpenFileName(self, '?????????????????? ???????????????????? ???? ????????????', '.', 'Text file (*.txt)')
        if not file:
            return
        self._cal_out_model.loadCalData(file)

    @pyqtSlot()
    def on_btnSaveOut_clicked(self):
        file, _ = QFileDialog.getSaveFileName(self, '?????????????????? ???????????????????? ???? ????????????', '.', 'Text file (*.txt)')
        if not file:
            return
        self._cal_out_model.saveCalData(file)

    def task(self):
        return [
            {
                'f': i['f'],
                'p': i['read_pow'],
                'p_ref': i['p'],
                'delta_in': i['delta'],
                'delta_out': o,
            }
            for i, o
            in zip(
                self._cal_in_model.calData(),
                cycle([v['delta'] for v in self._cal_out_model.calData()])
            )
        ]

    def is_ready(self):
        return self._cal_in_model.is_ready() and self._cal_out_model.is_ready()

    def saveCalData(self):
        if self._cal_in_model.is_ready():
            self._cal_in_model.saveCalData('default_cal_in.txt')
        if self._cal_out_model.is_ready():
            self._cal_out_model.saveCalData('default_cal_out.txt')
