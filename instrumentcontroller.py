import ast
import time

import numpy as np

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from forgot_again.file import load_ast_if_exists, pprint_to_file

from instr.instrumentfactory import mock_enabled, SourceFactory, PowerMeterFactory, GeneratorFactory
from measureresult import MeasureResult
from secondaryparams import SecondaryParams

GIGA = 1_000_000_000
MEGA = 1_000_000
KILO = 1_000
MILLI = 1 / 1_000


class InstrumentController(QObject):
    pointReady = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        addrs = load_ast_if_exists('instr.ini', default={
            'Генератор': 'GPIB1::18::INSTR',
            'Изм. мощности': 'GPIB1::3::INSTR',
            'Источник': 'GPIB1::9::INSTR',
        })

        self.requiredInstruments = {
            'Генератор': GeneratorFactory(addrs['Генератор']),
            'Изм. мощности': PowerMeterFactory(addrs['Изм. мощности']),
            'Источник': SourceFactory(addrs['Источник']),
        }

        self.deviceParams = {
            '---': {
                'F': 1,
            },
        }

        self.secondaryParams = SecondaryParams(required={
            'f_min': [
                'Fн=',
                {'start': 0.0, 'end': 10.0, 'step': 1.0, 'value': 1.0, 'suffix': ' ГГц'}
            ],
            'f_max': [
                'Fв=',
                {'start': 0.0, 'end': 10.0, 'step': 1.0, 'value': 1.0, 'suffix': ' ГГц'}
            ],
            'f_delta': [
                'ΔF=',
                {'start': 0.0, 'end': 10.0, 'step': 1.0, 'value': 1.0, 'suffix': ' ГГц'}
            ],
            'i_src_max': [
                'Iп.макс=',
                {'start': 0.0, 'end': 500.0, 'step': 1.0, 'value': 20.0, 'suffix': ' мА'}
            ],
            'u_src_max': [
                'Uп.=',
                {'start': 0.0, 'end': 12.0, 'step': 0.1, 'value': 3.0, 'suffix': ' В'}
            ],
            'sep_1': ['', {'value': None}],
            'avg': [
                'Уср.=',
                {'start': 0, 'end': 50, 'step': 1, 'value': 1, 'suffix': ''}
            ],
            'sep_2': ['', {'value': None}],
            'x_start': [
                'Xstart=',
                {'start': 0.0, 'end': 30.0, 'step': 0.5, 'value': 10.0, 'suffix': ' ?'}
            ],
            'x_scale': [
                'Xscale=',
                {'start': 0.0, 'end': 30.0, 'step': 0.5, 'value': 10.0, 'suffix': ' ?'}
            ],
            'y_start': [
                'Ystart=',
                {'start': 0.0, 'end': 30.0, 'step': 0.5, 'value': 10.0, 'suffix': ' ?'}
            ],
            'y_scale': [
                'Yscale=',
                {'start': 0.0, 'end': 30.0, 'step': 0.5, 'value': 10.0, 'suffix': ' ?'}
            ],
            'trig_level': [
                'Ур. сраб.=',
                {'start': 0.0, 'end': 30.0, 'step': 0.5, 'value': 10.0, 'suffix': ' ?'}
            ],
            'mark_1': [
                'Маркер 1=',
                {'start': 0.0, 'end': 30.0, 'step': 0.5, 'value': 10.0, 'suffix': ' ?'}
            ],
            'mark_2': [
                'Маркер 2=',
                {'start': 0.0, 'end': 30.0, 'step': 0.5, 'value': 10.0, 'suffix': ' ?'}
            ],
        }, file_name='params.ini')

        self._cal_in = load_ast_if_exists('cal_in.ini', default={})
        self._cal_out = load_ast_if_exists('cal_out.ini', default={})

        self._instruments = dict()

    def __str__(self):
        return f'{self._instruments}'

    # region connections
    def connect(self, **kwargs):
        addrs = kwargs.pop('addrs')
        fn_progress = kwargs.pop('fn_progress', None)

        print(f'searching for {addrs}')
        for k, v in addrs.items():
            self.requiredInstruments[k].addr = v

        ok = self._find()
        if ok:
            return ok, 'instruments found'
        else:
            return ok, 'instrument find error'

    def _find(self):
        self._instruments = {
            k: v.find() for k, v in self.requiredInstruments.items()
        }
        return all(self._instruments.values())
    # endregion

    # region calibrations
    def calibrateIn(self, **kwargs):
        report_fn = kwargs.pop('report_fn')
        token = kwargs.pop('token')
        params = kwargs.pop('params')
        print(f'call calibrate in with {report_fn} {token} {params}')

        for i in range(10):
            time.sleep(0.1)
            report_fn({'cal_in_index': i})

        return True, 'calibrate in done'

    def calibrateOut(self, **kwargs):
        report_fn = kwargs.pop('report_fn')
        token = kwargs.pop('token')
        params = kwargs.pop('params')
        print(f'call calibrate out with {report_fn} {token} {params}')

        for i in range(10):
            time.sleep(0.1)
            report_fn({'cal_out_index': i})

        return True, 'calibrate out done'
    # endregion

    # region initialization
    def _clear(self):
        pass

    def _init(self):
        self._instruments['Генератор'].send('*RST')
        self._instruments['Изм. мощности'].send('*RST')
        self._instruments['Источник'].send('*RST')
    # endregion

    def measure(self, **kwargs):
        report_fn = kwargs.pop('report_fn')
        token = kwargs.pop('token')
        params = kwargs.pop('params')
        print(f'call measure with {report_fn} {token} {params}')

        ok = self._measure(token, params, report_fn)
        if ok:
            return ok, 'measure success'
        else:
            return ok, 'measure error'

    def _measure(self, token, params, report_fn):
        self._clear()
        self._init()

        for i in range(10):
            time.sleep(0.1)
            report_fn({'measure': i})

        return True

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]
