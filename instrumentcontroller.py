import ast
import time

import numpy as np

from PyQt5.QtCore import QObject, pyqtSignal
from forgot_again.file import load_ast_if_exists

from instr.instrumentfactory import mock_enabled, SourceFactory, PowerMeterFactory, GeneratorFactory
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
                {'start': 0.0, 'end': 40.0, 'step': 1.0, 'value': 0.1, 'decimals': 3, 'suffix': ' ГГц'}
            ],
            'f_max': [
                'Fв=',
                {'start': 0.0, 'end': 40.0, 'step': 1.0, 'value': 0.3, 'decimals': 3, 'suffix': ' ГГц'}
            ],
            'f_delta': [
                'ΔF=',
                {'start': 0.0, 'end': 40.0, 'step': 1.0, 'value': 0.1, 'decimals': 3, 'suffix': ' ГГц'}
            ],
            'p_min': [
                'Pн=',
                {'start': -30.0, 'end': 30.0, 'step': 1.0, 'value': 0.0, 'suffix': ' дБм'}
            ],
            'p_max': [
                'Pв=',
                {'start': -30.0, 'end': 30.0, 'step': 1.0, 'value': 10.0, 'suffix': ' дБм'}
            ],
            'p_delta': [
                'ΔP=',
                {'start': 0.0, 'end': 30.0, 'step': 1.0, 'value': 5.0, 'suffix': ' дБм'}
            ],
            'i_src_max': [
                'Iп.макс=',
                {'start': 0.0, 'end': 500.0, 'step': 1.0, 'value': 20.0, 'suffix': ' мА'}
            ],
            'u_src': [
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
        params = kwargs.pop('params').params
        print(f'call calibrate in with {report_fn} {token} {params}')

        gen = self._instruments['Генератор']
        meter = self._instruments['Изм. мощности']

        f_min = params['f_min'] * GIGA
        f_max = params['f_max'] * GIGA
        f_delta = params['f_delta'] * GIGA
        p_min = params['p_min']
        p_max = params['p_max']
        p_delta = params['p_delta']

        avg = params['avg']

        pows = [round(x, 1) for x in np.arange(start=p_min, stop=p_max + 0.0001, step=p_delta)]
        freqs = [round(x) for x in np.arange(start=f_min, stop=f_max + 0.0001, step=f_delta)]

        self._init()

        meter.send(f'SENS1:AVER:COUN {avg}')
        meter.send('FORM ASCII')
        # meter.send('TRIG:SOUR INT1')
        # meter.send('INIT:CONT ON')

        # автоматическое измерение ошибается в первой точке, измеряем пустышку
        # почему - хз
        gen.send(f'POW {pows[0]}dbm')
        gen.send(f'FREQ {freqs[0]}')
        meter.send(f'SENS1:FREQ {freqs[0]}')
        gen.send('OUTP ON')
        meter.send('ABORT')
        meter.send('INIT')
        time.sleep(0.1)
        meter.query('FETCH?')

        index = 0
        if mock_enabled:
            with open('./mock_data/cal_in.txt', mode='rt', encoding='utf-8') as f:
                mocked_raw_data = ast.literal_eval(''.join(f.readlines()))

        result = []
        for p in pows:
            for f in freqs:
                gen.send(f'POW {p}dbm')
                gen.send(f'FREQ {f}')
                meter.send(f'SENS1:FREQ {f}')
                gen.send('OUTP ON')

                meter.send('ABORT')
                meter.send('INIT')

                time.sleep(0.1)

                read_pow = float(meter.query('FETCH?'))
                diff = p - read_pow
                delta = diff

                if not mock_enabled:
                    while abs(diff) > 0.05:
                        gen.send(f'POW {p + diff}dbm')

                        meter.send('ABORT')
                        meter.send('INIT')

                        time.sleep(0.1)

                        read_pow = float(meter.query('FETCH?'))

                        diff = p - read_pow

                raw_point = {
                    'f': f,
                    'p': p,
                    'read_pow': read_pow,
                    'delta': delta,
                }

                if mock_enabled:
                    raw_point = mocked_raw_data[index]
                    index += 1

                report_fn(raw_point)
                result.append(raw_point)

        gen.send('OUTP OFF')

        return True, 'calibrate in done'

    def calibrateOut(self, **kwargs):
        report_fn = kwargs.pop('report_fn')
        token = kwargs.pop('token')
        params = kwargs.pop('params').params
        cal_data = kwargs.pop('cal_data')

        print(f'call calibrate out with {report_fn} {token} {params}')

        gen = self._instruments['Генератор']
        meter = self._instruments['Изм. мощности']

        avg = params['avg']

        # gen.send('*RST')
        # meter.send('*RST')
        #
        # meter.send(f'SENS1:AVER:COUN {avg}')
        # meter.send('FORMat ASCII')
        # meter.send('TRIG:SOUR INT1')
        # meter.send('INIT:CONT ON')

        max_p = max(el['p'] for el in cal_data)
        cal_data = list(filter(lambda el: el['p'] == max_p, cal_data))
        point = cal_data[0]

        # автоматическое измерение ошибается в первой точке, измеряем пустышку
        # почему - хз
        gen.send(f'POW {point["p"]}dbm')
        gen.send(f'FREQ {point["f"]}')
        meter.send(f'SENS1:FREQ {point["f"]}')
        gen.send('OUTP ON')
        meter.send('ABORT')
        meter.send('INIT')
        time.sleep(0.1)
        meter.query('FETCH?')

        index = 0
        if mock_enabled:
            with open('./mock_data/cal_out.txt', mode='rt', encoding='utf-8') as f:
                mocked_raw_data = ast.literal_eval(''.join(f.readlines()))

        result = []
        for point in cal_data:
            p = point['p']
            f = point['f']

            gen.send(f'POW {p}dbm')
            gen.send(f'FREQ {f}')
            meter.send(f'SENS1:FREQ {f}')
            gen.send('OUTP ON')

            meter.send('ABORT')
            meter.send('INIT')

            time.sleep(0.1)

            read_pow = float(meter.query('FETCH?'))
            delta = p - read_pow

            point = {
                'f': f,
                'p': p,
                'read_pow': read_pow,
                'delta': delta,
            }

            if mock_enabled:
                point = mocked_raw_data[index]
                index += 1

            report_fn(point)
            result.append(point)

        gen.send('OUTP OFF')

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
        params = kwargs.pop('params').params
        task = kwargs.pop('task')
        print(f'call measure with {report_fn} {token} {params} {task}')

        ok = self._measure(token, params, report_fn, task)
        if ok:
            return ok, 'measure success'
        else:
            return ok, 'measure error'

    def _measure(self, token, params, report_fn, task):
        self._clear()
        self._init()

        gen = self._instruments['Генератор']
        meter = self._instruments['Изм. мощности']

        avg = params['avg']

        gen.send('*RST')
        meter.send('*RST')

        meter.send(f'SENS1:AVER:COUN {avg}')
        meter.send('FORMat ASCII')
        # meter.send('TRIG:SOUR INT1')
        # meter.send('INIT:CONT ON')

        point = task[0]
        # автоматическое измерение ошибается в первой точке, измеряем пустышку
        # почему - хз
        gen.send(f'POW {point["p"]}dbm')
        gen.send(f'FREQ {point["f"]}')
        meter.send(f'SENS1:FREQ {point["f"]}')
        gen.send('OUTP ON')
        meter.send('ABORT')
        meter.send('INIT')
        time.sleep(0.1)
        meter.query('FETCH?')

        result = []
        for row in task:
            p = row['p']
            f = row['f']
            delta_in = row['delta_in']
            delta_out = row['delta_out']

            gen.send(f'POW {p + delta_in}dbm')
            gen.send(f'FREQ {f}')
            meter.send(f'SENS1:FREQ {f}')
            gen.send('OUTP ON')

            meter.send('ABORT')
            meter.send('INIT')

            time.sleep(0.1)

            read_pow = float(meter.query('FETCH?'))
            adjusted_pow = read_pow + delta_out

            point = {
                'f': f,
                'p': p,
                'read_pow': read_pow,
                'adjusted_pow': adjusted_pow,
            }
            report_fn(point)
            result.append(point)

        gen.send('OUTP OFF')
        return True

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]
