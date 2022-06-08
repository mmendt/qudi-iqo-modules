# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware dummy for fast counting devices.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
import threading
import time
import inspect
from enum import IntEnum

import numpy as np
from pyspcm import *
from spcm_tools import *

from qudi.core.configoption import ConfigOption
from qudi.interface.fast_counter_interface import FastCounterInterface
from qudi.hardware.Fast_ADC.si_dataclass import *

class CardStatus(IntEnum):
    unconfigured = 0
    idle = 1
    running = 2
    paused = 3
    error = -1



def check_card_error(func):
    def wrapper(self, *args, **kwargs):
        value = func(self, *args, **kwargs)
        if self._error_check == True:
            error = self._error
            frame = inspect.currentframe().f_back
            module = inspect.getfile(func)

            if error != 0:
                print('line {} Error {} at {} {} '.format(frame.f_lineno, error, frame.f_code.co_name, module))
                szErrorTextBuffer = create_string_buffer(ERRORTEXTLEN)
                spcm_dwGetErrorInfo_i32(self._card, None, None, szErrorTextBuffer)
                print("{0}\n".format(szErrorTextBuffer.value))

            else:
                print('line {} no error at {}'.format(frame.f_lineno, frame.f_code.co_name))
        else:
            pass
        return value

    return wrapper



class Card_command():
    '''
    This class contains commands related to the start and stop of the card's actions.
    '''

    def __init__(self, card):
        self._card = card

    @check_card_error
    def card_start(self):
        self._error = spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_CARD_START)

    @check_card_error
    def card_stop(self):
        self._error = spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_CARD_STOP)

    @check_card_error
    def card_reset(self):
        self._error = spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_CARD_RESET)

    @check_card_error
    def enable_trigger(self):
        self._error = spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_CARD_ENABLETRIGGER)
        trigger_enabled = True
        return trigger_enabled

    @check_card_error
    def disable_trigger(self):
        self._error = spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_CARD_DISABLETRIGGER)
        trigger_enabled = False
        return trigger_enabled

    @check_card_error
    def force_trigger(self):
        spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_CARD_FORCETRIGGER)

    @check_card_error
    def start_dma(self):
        self._error = spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_DATA_STARTDMA)

    @check_card_error
    def stop_dma(self):
        self._error = spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_DATA_STOPDMA)

    @check_card_error
    def wait_DMA(self):
        self._error = spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_CARD_WAITREADY)


class Data_process_command(Card_command):
    '''
    This class contains commands to control the data acquistion.
    '''
    _dp_check = True
    _error_check = False

    def __init__(self, card):
        self._card = card

    def init_dp_params(self):
        self.status = 0
        self.avail_user_pos_B = '-----'
        self.avail_user_len_B = '-----'
        self.avail_card_len_B = '-----'
        self.trig_counter = '-----'
        self.processed_data_B = 0
        self.total_data_B = '-----'
        self.avg_num = 0

    def check_dp_status(self):
        self.get_status()
        self.get_avail_user_pos_B()
        self.get_avail_user_len_B()
        self.get_avail_user_reps()
        self.get_trig_counter()
        if self._dp_check == True:
            print("Stat:{0:04x}h Pos:{1:010}B Avail:{2:010}B "
                  "Processed:{3:010}B / {4}B: "
                  "Avail:{5} Avg:{6} / Trig:{7} \n".format(self.status,
                                                           self.avail_user_pos_B,
                                                           self.avail_user_len_B,
                                                           self.processed_data_B,
                                                           self.total_data_B,
                                                           self.avail_user_reps,
                                                           self.avg_num,
                                                           self.trig_counter)
                  )
        else:
            pass

    @check_card_error
    def get_status(self):
        status = int32()
        self._error = spcm_dwGetParam_i32(self._card, SPC_M2STATUS, byref(status))
        self.status = status.value
        return status.value

    @check_card_error
    def get_avail_user_len_B(self):
        c_avaiil_user_len = c_int64(0)
        self._error = spcm_dwGetParam_i64(self._card, SPC_DATA_AVAIL_USER_LEN, byref(c_avaiil_user_len))
        self.avail_user_len_B = c_avaiil_user_len.value
        return self.avail_user_len_B

    def get_avail_user_reps(self):
        self.avail_user_reps = int(np.floor(self.get_avail_user_len_B() / self.seq_size_B))
        return self.avail_user_reps

    @check_card_error
    def get_avail_user_pos_B(self):
        c_avaiil_user_pos = c_int64(0)
        self._error = spcm_dwGetParam_i64(self._card, SPC_DATA_AVAIL_USER_POS, byref(c_avaiil_user_pos))
        self.avail_user_pos_B = c_avaiil_user_pos.value
        return self.avail_user_pos_B

    @check_card_error
    def get_avail_card_len_B(self):
        c_avaiil_card_len_B = c_int64()
        self._error = spcm_dwGetParam_i64(self._card, SPC_DATA_AVAIL_CARD_LEN, byref(c_avaiil_card_len_B))
        self.avail_card_len_B = c_avaiil_card_len_B.value
        return self.avail_card_len_B

    #@check_card_error
    def set_avail_card_len_B(self, avail_card_len_B):
        self._error = c_avaiil_card_len_B = c_int32(avail_card_len_B)
        spcm_dwSetParam_i32(self._card, SPC_DATA_AVAIL_CARD_LEN, c_avaiil_card_len_B)
        self.processed_data_B = self.processed_data_B + avail_card_len_B
        return

    @check_card_error
    def get_trig_counter(self):
        c_trig_counter = c_int64()
        self._error = spcm_dwGetParam_i64(self._card, SPC_TRIGGERCOUNTER, byref(c_trig_counter))
        self.trig_counter = c_trig_counter.value
        return self.trig_counter

    @check_card_error
    def get_bits_per_sample(self):
        c_bits_per_sample = c_int32(0)
        self._error = spcm_dwGetParam_i32(self._card, SPC_MIINST_BITSPERSAMPLE, byref(c_bits_per_sample))
        return c_bits_per_sample.value


class Ts_process_command():

    def __init__(self, card):
        self._card = card

    def reset_ts_counter(self):
        spcm_dwSetParam_i32(self._card, SPC_TIMESTAMP_CMD, SPC_TS_RESET)

    def start_extra_dma(self):
        spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_EXTRA_STARTDMA)

    def wait_extra_dma(self):
        spcm_dwSetParam_i32(self._card, SPC_M2CMD, M2CMD_EXTRA_WAITDMA)

    def get_gate_len_alignment(self):
        c_gate_len_alignment = c_int64(0)
        self._error = spcm_dwGetParam_i64(self._card, SPC_GATE_LEN_ALIGNMENT, byref(c_gate_len_alignment))
        self.gate_len_alignment = c_gate_len_alignment.value
        return self.gate_len_alignment

    def get_ts_avail_user_len_B(self):
        c_ts_avaiil_user_len = c_int64(0)
        self._error = spcm_dwGetParam_i64(self._card, SPC_TS_AVAIL_USER_LEN, byref(c_ts_avaiil_user_len))
        self.ts_avail_user_len_B = c_ts_avaiil_user_len.value
        return self.ts_avail_user_len_B

    def get_ts_avail_user_pos_B(self):
        c_ts_avaiil_user_pos = c_int64(0)
        self._error = spcm_dwGetParam_i64(self._card, SPC_TS_AVAIL_USER_POS, byref(c_ts_avaiil_user_pos))
        self.ts_avail_user_pos_B = c_ts_avaiil_user_pos.value
        return self.ts_avail_user_pos_B

    def get_ts_avail_card_len_B(self):
        c_ts_avaiil_card_len_B = c_int64()
        self._error = spcm_dwGetParam_i64(self._card, SPC_TS_AVAIL_CARD_LEN, byref(c_ts_avaiil_card_len_B))
        self.ts_avail_card_len_B = c_ts_avaiil_card_len_B.value
        return self.ts_avail_card_len_B



class SpectrumInstrumentation(FastCounterInterface, Card_command):

    '''
    Hardware class for the spectrum instrumentation card
    Analog Inputs
    trigger_mode:
        'EXT' (External trigger),
        'SW' (Software trigger),
        'CH0' (Channel0 trigger)
    acquistion_mode:
        'STD_SINGLE'
        'STD_MULTI'
        'FIFO_SINGLE',
        'FIFO_GATE',
        'FIFO_MULTI',
        'FIFO_AVERAGE'

    Config example:

    si:
        module.Class: 'Fast_ADC.spectrum_instrumentation_ver1.SpectrumInstrumentation'
        ai_range_mV: 1000
        ai_offset_mV: 0
        ai_termination: '50Ohm'
        ai_coupling: 'AC'
        acq_mode: 'FIFO_MULTI'
        acq_HW_avg_num: 1
        acq_pre_trigger_samples: 16
        buf_notify_size: 4096
        clk_reference_Hz: 10e6
        trig_mode: 'EXT'
        trig_level_mV: 1000
        gated: False
        _init_buf_size_S: 1e9
    '''

    _modtype = 'SpectrumCard'
    _modclass = 'hardware'
    _error_check = False

    _ai_range_mV = ConfigOption('ai_range_mV', 1000, missing='warn')
    _ai_offset_mV = ConfigOption('ai_offset_mV', 0, missing='warn')
    _ai_term = ConfigOption('ai_termination', '50Ohm', missing='warn')
    _ai_coupling = ConfigOption('ai_coupling', 'DC', missing='warn')
    _acq_mode = ConfigOption('acq_mode', 'FIFO_MULTI', missing='warn')
    _acq_HW_avg_num = ConfigOption('acq_HW_avg_num', 1, missing='nothing')
    _acq_pre_trigs_S = ConfigOption('acq_pre_trigger_samples', 16, missing='warn')
    _acq_post_trigs_S = ConfigOption('acq_post_trigger_samples', 16, missing='nothing')

    _buf_notify_size_B = ConfigOption('buf_notify_size_B', 4096, missing='warn')
    _clk_ref_Hz = ConfigOption('clk_reference_Hz', 10e6, missing='warn')
    _trig_mode = ConfigOption('trig_mode', 'EXT', missing='warn')
    _trig_level_mV = ConfigOption('trig_level_mV', '1000', missing='warn')

    _gated = ConfigOption('gated', False, missing='warn')
    _init_buf_size_S = ConfigOption('initial_buffer_size_S', 1e9, missing='warn')


    _check_buffer = False
    _path_for_buffer_check = ConfigOption('path_for_buffer_check', 'C:',missing='nothing')
    _reps_for_buffer_check = ConfigOption('repititions_for_buffer_check', 1, missing='nothing')


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._card_on = False
        self._internal_status = CardStatus.idle

    def _load_settings_from_config_file(self):
        self.cs.ai_range_mV = int(self._ai_range_mV)
        self.cs.ai_offset_mV = int(self._ai_offset_mV)
        self.cs.ai_term = self._ai_term
        self.cs.ai_coupling = self._ai_coupling
        self.cs.acq_mode = self._acq_mode
        self.cs.acq_HW_avg_num = int(self._acq_HW_avg_num)
        self.cs.acq_pre_trigs_S = int(self._acq_pre_trigs_S)
        self.cs.acq_post_trigs_S = int(self._acq_post_trigs_S)
        self.cs.buf_notify_size_B = int(self._buf_notify_size_B)
        self.cs.clk_ref_Hz = int(self._clk_ref_Hz)
        self.cs.trig_mode = self._trig_mode
        self.cs.trig_level_mV = int(self._trig_level_mV)

        self.ms.gated = self._gated
        self.ms.init_buf_size_S = int(self._init_buf_size_S)
        self.ms.assign_data_bit(self.cs.acq_mode)

    def on_activate(self):
        """
        Open the card by activation of the module
        """

        if self._gated == True:
            self.cs = Card_settings_gated()
            self.ms = Measurement_settings_gated()
        else:
            self.cs = Card_settings()
            self.ms = Measurement_settings()

        self._load_settings_from_config_file()
        self.dp = Data_process_loop()
        self.cfg = Configure_command()

        if self._card_on == False:
            self.cs.card = spcm_hOpen(create_string_buffer(b'/dev/spcm0'))
            self._card_on = True

        else:
            self.log.info('SI card is already on')

        if self.cs.card == None:
            self.log.info('No card found')

    def on_deactivate(self):
        """
        Close the card
        """
        spcm_vClose(self.cs.card)

    def get_constraints(self):

        constraints = dict()

        constraints['possible_timebase_list'] = np.array([1, 2, 4, 5, 6, 7, 8, 9, 10, 20, 50, 100, 200, 500, 1e3, 2e3, 5e3, 1e4])
        constraints['hardware_binwidth_list'] = (constraints['possible_timebase_list']) / 250e6 #maximum sampling rate 250 MHz
#        constraints['hardware_binwidth_list'] = 1

        return constraints

    def configure(self, binwidth_s, record_length_s, number_of_gates=0):
        """
        Configure the card parameters.
        @param float binwidth_s: Length of a single time bin in the time trace
                                  histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each single
                                      gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse
                                    sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, gate_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual set gate length in seconds
                    number_of_gates: the number of gated, which are accepted
        """
        self.cfg.load_static_cfg_params(self.cs, self.ms)

        self.ms.load_dynamic_params(binwidth_s, record_length_s, number_of_gates)
        self.cs.calc_dynamic_cs(self.ms.gated, binwidth_s, record_length_s)
        self.ms.calc_data_size_S(self.cs.acq_pre_trigs_S, self.cs.acq_post_trigs_S, self.cs.acq_seg_size_S)
        self.ms.calc_buf_params()
        self.cs.get_buf_size_B(self.ms.seq_size_B, self.ms.reps_per_buf)

        self.dp.init_process(self.cs, self.ms)
        self.cfg.load_dynamic_cfg_params(self.cs)

        self.cfg.configure_all()

        self.ms.c_buf_ptr = self.cfg.return_c_buf_ptr()
        if self.ms.gated == True:
            self.ms.c_ts_buf_ptr = self.cfg.return_c_ts_buf_ptr()

        return self.ms.binwidth_s, self.ms.actual_length, self.ms.number_of_gates

    def get_status(self):
        """
        Receives the current status of the Fast Counter and outputs it as
                    return value.

                0 = unconfigured
                1 = idle
                2 = running
                3 = paused
                -1 = error state
        """
        return self._internal_status

    def start_measure(self):
        """
        Start the acquistion and data process loop
        """
        self._internal_status = CardStatus.running
        self.log.info('Measurement started')
        self.configure(self.ms.binwidth_s, self.ms.actual_length, self.ms.number_of_gates)
        self._start_card()
        self.dp.init_measure_params()
        self.dp.start_data_process()

        return 0

    def _start_card(self):
        self._internal_status = CardStatus.running
        self.card_start()
        self.dp.trigger_enabled = self.enable_trigger()
        self.start_dma()
        self.dp.wait_DMA()

    def get_data_trace(self):
        """
        Fetch the averaged data so far.
        """
        self.dp.check_dp_status()
        avg_data, avg_num = self.dp.fetch_data_trace()
        info_dict = {'elapsed_sweeps': avg_num, 'elapsed_time': time.time() - self.dp.start_time}

        return avg_data, info_dict

    def stop_measure(self):
        if self._internal_status == CardStatus.running:
            self.log.info('card stopped')
            self.dp.stop_data_process()
            self.disable_trigger()
            self.stop_dma()
            self.card_stop()

        self._internal_status = CardStatus.idle
        self.dp.loop_on = False
        self.log.info('Measurement stopped')

        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

            Fast counter must be initially in the run state to make it pause.
        """
        self.disable_trigger()
        self.dp.loop_on = False
        self.dp.stop_data_process()

        self._internal_status = CardStatus.paused
        self.log.info('Measurement paused')
        return


    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        self.log.info('Measurement continued')
        self._internal_status = CardStatus.running
        self.dp.loop_on = True
        self.dp.trigger_enabled = self.enable_trigger()
        self.dp.start_data_process()

        return 0

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        return self.ms.gated

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)
        """
        return self.ms.binwidth_s


class Configure_acquistion_mode():
    def set_acquistion_mode(self, card, acq_mode, pre_trigs_S, post_trigs_S, seg_size_S, loops, HW_avg_num):

        if acq_mode == 'STD_SINGLE':
            self._mode_STD_SINGLE(card, post_trigs_S, seg_size_S)

        elif acq_mode == 'STD_MULTI':
            self._mode_STD_MULTI(card, post_trigs_S, seg_size_S, loops)

        elif acq_mode == 'FIFO_SINGLE':
            self._mode_FIFO_SINGLE(card, pre_trigs_S, seg_size_S, loops)

        elif acq_mode == 'FIFO_GATE':
            self._mode_FIFO_GATE(card, pre_trigs_S, post_trigs_S, loops)

        elif acq_mode == 'FIFO_MULTI':
            self._mode_FIFO_MULTI(card, post_trigs_S, seg_size_S, loops)

        elif acq_mode == 'FIFO_AVERAGE':
            self._mode_FIFO_AVERAGE(card, post_trigs_S, seg_size_S, loops, HW_avg_num)

    @check_card_error
    def _mode_STD_SINGLE(self, card, post_trigs_S, seg_size_S):
        spcm_dwSetParam_i32(card, SPC_CARDMODE, SPC_REC_STD_SINGLE)
        spcm_dwSetParam_i32(card, SPC_MEMSIZE, seg_size_S)
        self._error = spcm_dwSetParam_i32(card, SPC_POSTTRIGGER, post_trigs_S)
        return

    @check_card_error
    def _mode_STD_MULTI(self, card, post_trigs_S, seg_size_S, loops):
        spcm_dwSetParam_i32(card, SPC_CARDMODE, SPC_REC_STD_MULTI)
        spcm_dwSetParam_i32(card, SPC_SEGMENTSIZE, seg_size_S)
        spcm_dwSetParam_i32(card, SPC_MEMSIZE, int(seg_size_S * loops))
        self._error = spcm_dwSetParam_i32(card, SPC_POSTTRIGGER, post_trigs_S)

        return

    @check_card_error
    def _mode_FIFO_SINGLE(self, card, pre_trigs_S, seg_size_S, loops=1):
        spcm_dwSetParam_i32(card, SPC_CARDMODE, SPC_REC_FIFO_SINGLE)
        spcm_dwSetParam_i32(card, SPC_PRETRIGGER, pre_trigs_S)
        spcm_dwSetParam_i32(card, SPC_SEGMENTSIZE, seg_size_S)
        self._error = spcm_dwSetParam_i32(card, SPC_LOOPS, loops)
        return

    @check_card_error
    def _mode_FIFO_GATE(self, card, pre_trigs_S, post_trigs_S, loops=0):
        spcm_dwSetParam_i32(card, SPC_CARDMODE, SPC_REC_FIFO_GATE)
        spcm_dwSetParam_i32(card, SPC_PRETRIGGER, pre_trigs_S)
        spcm_dwSetParam_i32(card, SPC_POSTTRIGGER, post_trigs_S)
        self._error = spcm_dwSetParam_i32(card, SPC_LOOPS, loops)
        return

    @check_card_error
    def _mode_FIFO_MULTI(self, card, post_trigs_S, seg_size_S, loops=0):
        spcm_dwSetParam_i32(card, SPC_CARDMODE, SPC_REC_FIFO_MULTI)
        spcm_dwSetParam_i32(card, SPC_SEGMENTSIZE, seg_size_S)
        spcm_dwSetParam_i32(card, SPC_POSTTRIGGER, post_trigs_S)
        self._error = spcm_dwSetParam_i32(card, SPC_LOOPS, loops)
        return

    @check_card_error
    def _mode_FIFO_AVERAGE(self, card, post_trigs_S, seg_size_S, loops=0):#,HW_avg_num):
        max_post_trigs_S = 127984

        spcm_dwSetParam_i32(card, SPC_CARDMODE, SPC_REC_FIFO_AVERAGE)
        spcm_dwSetParam_i32(card, SPC_AVERAGES, HW_avg_num)
        spcm_dwSetParam_i32(card, SPC_SEGMENTSIZE, seg_size_S)
        spcm_dwSetParam_i32(card, SPC_POSTTRIGGER, post_trigs_S)
        self._error = spcm_dwSetParam_i32(card, SPC_LOOPS, loops)
        return

class Configure_trigger():
    def set_trigger(self, card, trig_mode, trig_level_mV):

        if trig_mode == 'EXT':
            self._trigger_EXT(card, trig_level_mV)

        elif trig_mode == 'SW':
            self._trigger_SW(card)

        elif trig_mode == 'CH0':
            self._trigger_CH0(card, trig_level_mV)

    @check_card_error
    def _trigger_EXT(self, card, trig_level_mV):
        spcm_dwSetParam_i32(card, SPC_TRIG_EXT0_MODE, SPC_TM_POS)
        spcm_dwSetParam_i32(card, SPC_TRIG_EXT0_LEVEL0, trig_level_mV)
        spcm_dwSetParam_i32(card, SPC_TRIG_ORMASK, SPC_TMASK_EXT0)
        self._error = spcm_dwSetParam_i32(card, SPC_TRIG_ANDMASK, 0)

    @check_card_error
    def _trigger_SW(self, card):
        spcm_dwSetParam_i32(card, SPC_TRIG_ORMASK, SPC_TMASK_SOFTWARE)
        self._error = spcm_dwSetParam_i32(card, SPC_TRIG_ANDMASK, 0)

    @check_card_error
    def _trigger_CH0(self, card, trig_level_mV):
        spcm_dwSetParam_i32(card, SPC_TRIG_ORMASK, SPC_TMASK_NONE)
        spcm_dwSetParam_i32(card, SPC_TRIG_CH_ANDMASK0, SPC_TMASK0_CH0)
        spcm_dwSetParam_i32(card, SPC_TRIG_CH0_LEVEL0, trig_level_mV)
        self._error = spcm_dwSetParam_i32(card, SPC_TRIG_CH0_MODE, SPC_TM_POS)





class Configure_data_transfer():
    def configure_data_transfer(self, card, c_buf_ptr, buf_size_B, buf_notify_size_B):
        c_buf_ptr = self.set_buffer(card, c_buf_ptr, buf_size_B)
        self.set_data_transfer(card, c_buf_ptr, buf_size_B, buf_notify_size_B)
        return c_buf_ptr

    def set_buffer(self, card, c_buf_ptr, buf_size_B):
        cont_buf_len = self.get_cont_buf_len(card, c_buf_ptr)
        if cont_buf_len > buf_size_B:
            print('Use continuour buffer')
        else:
            c_buf_ptr = pvAllocMemPageAligned(buf_size_B)
            print('User Scatter gather')

        return c_buf_ptr

    def get_cont_buf_len(self, card, c_buf_ptr):
        c_cont_buf_len = uint64(0)
        spcm_dwGetContBuf_i64(card, SPCM_BUF_DATA, byref(c_buf_ptr), byref(c_cont_buf_len))
        return c_cont_buf_len.value


    def pvAllocMemPageAligned(self, qwBytes):
        dwAlignment = 4096
        dwMask = dwAlignment - 1

        # allocate non-aligned, slightly larger buffer
        qwRequiredNonAlignedBytes = qwBytes * sizeof(c_char) + dwMask
        pvNonAlignedBuf = (c_char * qwRequiredNonAlignedBytes)()

        # get offset of next aligned address in non-aligned buffer
        misalignment = addressof(pvNonAlignedBuf) & dwMask
        if misalignment:
            dwOffset = dwAlignment - misalignment
        else:
            dwOffset = 0
        return (c_char * qwBytes).from_buffer(pvNonAlignedBuf, dwOffset)

    def set_data_transfer(self, card, c_buf_ptr, buf_size_B, buf_notify_size_B):
        c_buf_offset = uint64(0)
        c_buf_size_B = uint64(buf_size_B)

        spcm_dwDefTransfer_i64(card, SPCM_BUF_DATA, SPCM_DIR_CARDTOPC,
                                       buf_notify_size_B, byref(c_buf_ptr),
                                       c_buf_offset, c_buf_size_B
                                       )
        return

class Configure_command(Configure_acquistion_mode, Configure_trigger, Configure_data_transfer):
    '''
    This class contains methods to configure the card.
    '''

    def load_static_cfg_params(self, cs, ms):
        print('card = {} at Cfg'.format(cs.card))

        self._gated = ms.gated
        self._card = cs.card
        print('self._card = {} at Cfg'.format(self._card))

        self._c_buf_ptr = ms.return_c_buf_ptr()
        self._ai_range_mV = cs.ai_range_mV
        self._ai_offset_mV =cs.ai_offset_mV
        self._ai_term = cs.ai_term
        self._ai_coupling = cs.ai_coupling
        self._acq_mode = cs.acq_mode
        self._acq_HW_avg_num = cs.acq_HW_avg_num
        self._acq_pre_trigs_S = cs.acq_pre_trigs_S
        self._acq_loops = cs.acq_loops
        self._buf_notify_size_B = cs.buf_notify_size_B
        self._clk_samplerate_Hz = int(cs.clk_samplerate_Hz)
        self._clk_ref_Hz = int(cs.clk_ref_Hz)
        self._trig_mode = cs.trig_mode
        self._trig_level_mV = cs.trig_level_mV
        if self._gated == True:
            self._c_ts_buf_ptr = ms.return_c_ts_buf_ptr()
            self._ts_buf_size_B = cs.ts_buf_size_B
            self._ts_buf_notify_size_B = cs.ts_buf_notify_size_B

        self._error_check = True
        self.reg = Configure_register_checker(self._card)


    def load_dynamic_cfg_params(self, cs):
        self._acq_post_trigs_S = cs.acq_post_trigs_S
        self._acq_seg_size_S = cs.acq_seg_size_S
        self._buf_size_B = cs.buf_size_B

    def configure_all(self):

        self.set_analog_input_conditions(self._card)
        self.set_acquistion_mode(self._card, self._acq_mode, self._acq_pre_trigs_S, self._acq_post_trigs_S,
                                 self._acq_seg_size_S, self._acq_loops, self._acq_HW_avg_num)
        self.set_sampling_clock(self._card)
        self.set_trigger(self._card, self._trig_mode, self._trig_level_mV)
        self._c_buf_ptr = self.configure_data_transfer(self._card, self._c_buf_ptr, self._buf_size_B, self._buf_notify_size_B)
        if self._gated == True:
            self._c_ts_buf_ptr = self.configure_data_transfer(self._card, self._c_ts_buf_ptr, self._ts_buf_size_B, self._ts_buf_notify_size_B)

    @check_card_error
    def set_analog_input_conditions(self, card):
        ai_term_dict = {'1Mohm':0, '50Ohm':1}
        ai_coupling_dict = {'DC':0, 'AC':1}
        spcm_dwSetParam_i32(card, SPC_TIMEOUT, 5000)
        spcm_dwSetParam_i32(card, SPC_CHENABLE, CHANNEL0)
        spcm_dwSetParam_i32(card, SPC_AMP0, self._ai_range_mV) # +- 10 V
        spcm_dwSetParam_i32(card, SPC_OFFS0, self._ai_offset_mV)
        spcm_dwSetParam_i32(card, SPC_50OHM0, ai_term_dict[self._ai_term]) # A "1"("0") sets the 50(1M) ohm termination
        self._error = spcm_dwSetParam_i32(card, SPC_ACDC0, ai_coupling_dict[self._ai_coupling])  # A "0"("1") sets he DC(AC)coupling
        return


    @check_card_error
    def set_sampling_clock(self, card):
        spcm_dwSetParam_i32(card, SPC_CLOCKMODE, SPC_CM_INTPLL)
        spcm_dwSetParam_i32(card, SPC_REFERENCECLOCK, self._clk_ref_Hz)
        spcm_dwSetParam_i32(card, SPC_SAMPLERATE, self._clk_samplerate_Hz)
        self._error = spcm_dwSetParam_i32(card, SPC_CLOCKOUT, 1)
        return

    def return_c_buf_ptr(self):
        return self._c_buf_ptr

    def return_c_ts_buf_ptr(self):
        return self._c_ts_buf_ptr

class Configure_register_checker():
    def __init__(self, card):
        print('card = {} at CSR'.format(card))
        self._card = card
        print('self._card = {} at CSR'.format(self._card))

    def check_cs_registers(self):
        '''
        This method can be used to check the card settings registered in the card.
        '''
        self.csr = Card_settings()
        self._error_check = True
        self._check_csr_ai()
        self._check_csr_acq()
        self._check_csr_clk()
        self._check_csr_trig()

    @check_card_error
    def _check_csr_ai(self):
        ai_term_dict = {0:'1Mohm', 1:'50Ohm'}
        ai_coupling_dict = {0:'DC', 1:'AC'}

        c_ai_range_mV = c_int32()
        c_ai_offset_mV = c_int32()
        c_ai_term = c_int32()
        c_ai_coupling = c_int32()
        spcm_dwGetParam_i32(self._card, SPC_AMP0, byref(c_ai_range_mV)) # +- 10 V
        spcm_dwGetParam_i32(self._card, SPC_OFFS0, byref(c_ai_offset_mV))
        spcm_dwGetParam_i32(self._card, SPC_50OHM0, byref(c_ai_term))
        self._error = spcm_dwGetParam_i32(self._card, SPC_ACDC0, byref(c_ai_coupling))
        self.csr.ai_range_mV = int(c_ai_range_mV.value)
        self.csr.ai_offset_mV = int(c_ai_offset_mV.value)
        self.csr.ai_term = ai_term_dict[c_ai_term.value]
        self.csr.ai_coupling = ai_coupling_dict[c_ai_coupling.value]

    @check_card_error
    def _check_csr_acq(self):
        c_acq_mode = c_int32()
        c_acq_HW_avg_num = c_int32()
        c_acq_pre_trigs_S = c_int32()
        c_acq_post_trigs_S = c_int32()
        c_acq_mem_size_S = c_int32()
        c_acq_seg_size_S = c_int32()
        spcm_dwGetParam_i32(self._card, SPC_CARDMODE, byref(c_acq_mode))
        spcm_dwGetParam_i32(self._card, SPC_AVERAGES, byref(c_acq_HW_avg_num))
        spcm_dwGetParam_i32(self._card, SPC_PRETRIGGER, byref(c_acq_pre_trigs_S))
        spcm_dwGetParam_i32(self._card, SPC_POSTTRIGGER, byref(c_acq_post_trigs_S))
        spcm_dwGetParam_i32(self._card, SPC_MEMSIZE, byref(c_acq_mem_size_S))
        self._error = spcm_dwGetParam_i32(self._card, SPC_SEGMENTSIZE, byref(c_acq_seg_size_S))
        self.csr.acq_mode = c_acq_mode.value
        self.csr.acq_HW_avg_num = int(c_acq_HW_avg_num.value)
        self.csr.acq_pre_trigs_S = int(c_acq_pre_trigs_S.value)
        self.csr.acq_post_trigs_S = int(c_acq_post_trigs_S.value)
        self.csr.acq_mem_size_S = int(c_acq_mem_size_S.value)
        self.csr.acq_seg_size_S = int(c_acq_seg_size_S.value)

    @check_card_error
    def _check_csr_clk(self):
        c_clk_samplerate_Hz = c_int32()
        c_clk_ref_Hz = c_int32()
        spcm_dwGetParam_i32(self._card, SPC_REFERENCECLOCK, byref(c_clk_ref_Hz))
        self._error = spcm_dwGetParam_i32(self._card, SPC_SAMPLERATE, byref(c_clk_samplerate_Hz))
        self.csr.clk_samplerate_Hz = int(c_clk_samplerate_Hz.value)
        self.csr.clk_ref_Hz = int(c_clk_ref_Hz.value)

    @check_card_error
    def _check_csr_trig(self):
        c_trig_mode = c_int32()
        c_trig_level_mV = c_int32()
        spcm_dwGetParam_i32(self._card, SPC_TRIG_EXT0_MODE, byref(c_trig_mode))
        self._error = spcm_dwGetParam_i32(self._card, SPC_TRIG_EXT0_LEVEL0, byref(c_trig_level_mV))
        self.csr.trig_mode = c_trig_mode.value
        self.csr.trig_level_mV = int(c_trig_level_mV.value)


class Data_transfer:

    def __init__(self, c_buf_ptr, data_type, data_bytes_B, seq_size_S, reps_per_buf):
        self.c_buf_ptr = c_buf_ptr
        self.data_type = data_type
        self.data_bytes_B = data_bytes_B
        self.seq_size_S = seq_size_S
        self.seq_size_B = seq_size_S * self.data_bytes_B
        self.reps_per_buf = reps_per_buf

    def _cast_buf_ptr(self, user_pos_B):
        c_buffer = cast(addressof(self.c_buf_ptr) + user_pos_B, POINTER(self.data_type))
        return c_buffer

    def _asnparray(self, c_buffer, shape):
        np_buffer = np.ctypeslib.as_array(c_buffer, shape=shape)
        return np_buffer

    def _fetch_from_buf(self, user_pos_B, sample_S, data_type):
        shape = (sample_S,)
        c_buffer = self._cast_buf_ptr(user_pos_B)
        np_buffer = self._asnparray(c_buffer, shape)
        return np_buffer

    def get_new_data(self, curr_avail_reps, user_pos_B):
        rep_end = int(user_pos_B / self.seq_size_B) + curr_avail_reps

        if 0 < rep_end <= self.reps_per_buf:
            np_data = self._fetch_data(user_pos_B, curr_avail_reps)

        elif self.reps_per_buf < rep_end < 2 * self.reps_per_buf:
            np_data = self._fetch_data_buf_end(user_pos_B, curr_avail_reps)
        else:
            print('error: rep_end {} is out of range'.format(rep_end))

        return np_data

    def _fetch_data(self, user_pos_B, curr_avail_reps):
        np_data = self._fetch_from_buf(user_pos_B, curr_avail_reps * self.seq_size_S)
        return np_data

    def _fetch_data_buf_end(self, user_pos_B, curr_avail_reps):
        start_rep = int((user_pos_B / self.seq_size_B) + 1)
        reps_tail = self.reps_per_buf - (start_rep - 1)
        reps_head = curr_avail_reps - reps_tail

        np_data_tail = self._fetch_data(user_pos_B, reps_tail)
        np_data_head = self._fetch_data(0, reps_head)
        np_data = np.append(np_data_tail, np_data_head)

        return np_data


class Data_fetch_ungated():

    def __init__(self , cs, ms):
        self.ms = ms
        self.cs = cs
    def init_data_fetch(self):
        self.input_params(self.cs, self.ms)
        self.create_data_trsnsfer()

    def input_params(self, cs, ms):
        self.c_buf_ptr = ms.c_buf_ptr
        self.data_type = ms.get_data_type()
        self.data_bytes_B = ms.get_data_bytes_B()
        self.seq_size_S = ms.seq_size_S
        self.seq_size_B = self.seq_size_S * self.data_bytes_B
        self.dpcmd = Data_process_command(cs.card)

    def create_data_trsnsfer(self):
        self.hw_dt = Data_transfer(self.c_buf_ptr, self.data_type,
                                   self.data_bytes_B, self.seq_size_S)

    def fetch_data_to_dc(self, curr_avail_reps , dc):
        user_pos_B = self.dpcmd.get_avail_user_pos_B()
        dc.data = self.hw_dt.get_new_data(curr_avail_reps, user_pos_B)
        self.dpcmd.set_avail_card_len_B(curr_avail_reps * self.seq_size_B)
        dc.rep = curr_avail_reps
        return dc.data

class Data_fetch_gated(Data_fetch_ungated):
    def input_params(self, cs, ms):
        super().input_params(cs, ms)
        self.c_ts_buf_ptr = ms.c_ts_buf_ptr
        self.ts_data_type =  ms.get_data_bytes_B()
        self.ts_data_bytes_B = ms.ts_data_bytes_B

        self.tscmd = Ts_process_command()


    def create_data_trsnsfer(self):
        super().create_data_trsnsfer()
        seq_size = 2
        self.ts_dt = Data_transfer(self.c_ts_buf_ptr, self.ts_data_type,
                                   self.ts_data_bytes_B, seq_size)

    def fetch_data_to_dc(self, curr_avail_reps, dc):
        super().fetch_data_to_dc()
        ts_user_pos_B = self.tscmd.get_ts_avail_user_pos_B()
        ts_row = self.ts_dt.get_new_data(curr_avail_reps, ts_user_pos_B)
        dc.ts_r = ts_row[::2]
        dc.ts_f = ts_row[1::2]



class Data_process():

    def init_data_procses(self, cs, ms):
        self._input_settings_to_dp(cs, ms)
        self._generate_data_cls()

    def _input_settings_to_dp(self, cs, ms):
        self.ms = ms
        self.cs = cs

    def _generate_data_cls(self):
        if self.ms.gated == True:
            self.dc = SeqDataMultiGated()
            self.df = Data_fetch_gated(self.cs, self.ms)
        else:
            self.dc = SeqDataMulti()
            self.df = Data_fetch_ungated(self.cs, self.ms)

        self.avg = AvgData()

    def get_new_avg_data(self):
        self.new_avg = AvgData()
        avg_num, avg_data = self.dc.avgdata()
        self.new_avg.add(avg_num, avg_data)

    def update_avg_data(self):
        self.avg.update(self.new_avg)

class Card_process():

    def init_card_process(self, cs):
        self._input_settings_to_cp(cs)
        self._generate_data_process_command()

    def _input_settings_to_cp(self, cs):
        self.cs = cs

    def _generate_data_process_command(self):
        self.dp = Data_process_command(self.cs.card)

    def _toggle_trigger(self, trigger_on):
        if trigger_on == self.trigger_enabled:
            return
        else:
            if trigger_on == True:
                self.trigger_enabled = self.dp.enable_trigger()
            elif trigger_on == False:
                self.trigger_enabled = self.dp.disable_trigger()

    def _wait_new_trigger(self, wait_trig_on):
        if wait_trig_on == True:
            print('waiting for triggers')
            prev_trig_counts = self.dp.trig_counter
            curr_trig_counts = self.dp.get_trig_counter()
            while curr_trig_counts == prev_trig_counts:
                    curr_trig_counts = self.dp.get_trig_counter()
            print('got_new_triggs {}'.format(curr_trig_counts))

            return curr_trig_counts

    def _wait_new_avail_reps(self):
        curr_avail_reps = self.dp.get_avail_user_reps()
        while curr_avail_reps == 0:
            curr_avail_reps = self.dp.get_avail_user_reps()

        return curr_avail_reps


class Data_process_commander(Data_process, Card_process):
    '''
    This class contains the command to be executed in a single loop body.
    '''

    def init_process(self, cs, ms):
        self.init_data_procses(cs, ms)
        self.init_card_process(cs)


    def command_process(self):
        unprocessed_reps = self.trig_counter - self.avg.num
        if unprocessed_reps == 0:
            print('wait new trigger')
            self.trigger_on = True
            self.wait_trigger_on = True
            self.data_process_on = False

        elif unprocessed_reps < 2 * self.ms.reps_per_buf:
            print('process data with trigger on')
            self.trigger_on = True
            self.wait_trigger_on = False
            self.data_process_on = True

        elif unprocessed_reps >= 2 * self.ms.reps_per_buf:
            print('process data with trigger off')
            self.trigger_on = False
            self.wait_trigger_on = False
            self.data_process_on = True

        self._toggle_trigger(self.trigger_on)

        self._process_data_with_trigger_off()




class Data_process_loop(Data_process_commander):
    '''
    This is the main data process loop class.
    '''



    def init_measure_params(self):
        self.init_dp_params()
        self.start_time = time.time()
        self.loop_on = True
        self.fetch_on = False

    def start_data_process(self):
        self.data_proc_th = threading.Thread(target=self.start_data_process_loop)
        self.data_proc_th.start()

        return

    def stop_data_process(self):

        self.loop_on = False
        self.data_proc_th.join()

    def start_data_process_loop(self):

        while self.loop_on == True:
            if self.fetch_on == False:
                self.check_dp_status()
                self.command_process()
                time.sleep(1e-6)
            elif self.fetch_on == True:
                print('fetching')
            else:
                print('error on loop')

        return

    def start_data_process_loop(self, n):

        while self.avg_num <= n:
            if self.fetch_on == False:
                self.check_dp_status()
                self.command_process()
                time.sleep(1e-6)
            elif self.fetch_on == True:
                print('fetching')
            else:
                print('error on loop')

        return


    def fetch_data_trace(self):
        self.fetch_on = True
        avg_data = self.avg_data
        avg_num = self.avg_num
        self.fetch_on = False
        return avg_data, avg_num


class SpectrumInstrumentationTest(SpectrumInstrumentation):

    def _set_params_test_exe(self, buf_length_S=1e7, notify_size_B =64):
        self.cs.acq_mode = 'STD_SINGLE'
        self.cs.trig_mode = 'SW'
        self.ms.binwidth_s = 1 / 250e6
        self.ms.record_length_s = 1e-6
        self.ms.number_of_gates = 0
        self.ms.init_buf_size_S = buf_length_S
        self.cs.buf_notify_size_B = notify_size_B

    def _start_card(self):
        self.configure(self.ms.binwidth_s, self.ms.record_length_s, self.ms.number_of_gates)
        self.dp.init_measure_params()
        self.dp.check_dp_status()
        self.card_start()
        self.dp.check_dp_status()
        self.start_dma()
        self.dp.check_dp_status()

    def _start_card_with_trigger(self):
        self.dp.init_measure_params()
        self.dp.check_dp_status()
        self.card_start()
        self.dp.check_dp_status()
        self.dp.trigger_enabled = self.enable_trigger()
        self.dp.check_dp_status()
        self.start_dma()
        self.dp.check_dp_status()



    def test_status(self, buf_length_S=1e7, notify_size_B=64):
        '''
        - Check if avail_user_len increases
        - Check if the avail_user_len decreases after set_avail_card_len
        - check if the user_pos shifts
        '''
        self._set_params_test_exe(buf_length_S, notify_size_B)
        self._start_card()
        self.dp.set_avail_card_len_B(100)
        self.dp.check_dp_status()

    def test_get_per_notify(self):
        '''
        - Check if the process data increases
        - Check if the data size corresponds to the segment size
        '''
        self._set_params_test_exe()
        self._start_card()
        self.avg_data, a = self.dp._process_one_rep_per_notify()

    def test_get_by_mean(self):
        self._set_params_test_exe()
        self._start_card()
        self.dp.avg_data = self.dp._fetch_reps_by_mean(0, 1)


    def test_trigger(self):
        '''
        - Check if the avail_user_length increases only after the trigger is input.
        '''
        self._set_params_test_exe()
        self.cs.trig_mode = 'EXT'
        self._start_card_with_trigger()

    def test_std_multi(self):
        '''
        - Check if the trigger counter corresponds to the given loop number
        - Check if the avail_user_len_B corresponds to the buf_size_B
        '''
        self._set_params_test_exe()
        self.cs.acq_mode = 'STD_MULTI'
        self.cs.trig_mode = 'EXT'
        self.ms.init_buf_size_S = 2000
        self.cfg._loops = 10
        self._start_card_with_trigger()

    def check_each_rep(self):
        import  matplotlib.pyplot as plt
        fig, ax = plt.subplots()

        sweeps = np.empty(0)
        for i in range(10):
            sweeps = np.append(sweeps, self.dp.process_data_by_mean(1))
            ax.plot(sweeps[i])
        plt.show()

    def check_average(self):
        '''
        - Check if the average number is correct
        - Check if the average across the buffer end is done
        '''
        self.dp.initial_reps = False
        self.sweep1 = 1
        self.sweep2 = self.cfg._loops - self.sweep1
        self.avg_data_1, self.avg_num_1 = self.dp.process_data_by_mean(self.sweep1)
        self.dp.check_dp_status()
        self.avg_data_2, self.avg_num_2 = self.dp.process_data_by_mean(self.sweep2)
        self.avg_data, self.avg_num = self.dp._weighted_avg_data(self.avg_data_1, self.sweep1,
                                                               self.avg_data_2, self.sweep2)

    def test_std_multi_more_reps(self):
        self._set_params_test_exe()
        self.cs.acq_mode = 'STD_MULTI'
        self.cs.trig_mode = 'EXT'
        self.ms.init_buf_size_S = 1e7
        self.cfg._loops = 60000
        self._start_card_with_trigger()
        self.dp.check_dp_status()


    def start_data_process_loop(self, n):
        '''
        - Check if the first acquistion is limited by the buffersize
        - Check if the later acquistion is done
        '''
        print('start_data_process_loop')

        for i in range(n):
            if self.dp.fetch_on == False:
                self.dp.check_dp_status()
                curr_avail_reps = self.dp.get_avail_user_reps()
                new_avg_data, new_avg_num = self.dp.process_data_by_mean(curr_avail_reps)
                self.dp.avg_data, self.dp.avg_num = self.dp._weighted_avg_data(self.dp.avg_data, self.dp.avg_num,
                                                                    new_avg_data, new_avg_num)
                self.dp.check_dp_status()
            else:
                print('fetching')
        print('end_data_process_loop')

        return


    def check_dp_loop(self):
        time_start = time.time()
        while self.dp.loop_on == True:
            current_time = time.time() - time_start
            if current_time < 5:
                self.dp.check_dp_status()
                self.dp.command_process()
            else:
                print('time = {}'.format(current_time))
                return
        return

    def check_loop(self):
        '''
        - Check if the trigger count increases
        -
        '''
        self.dp.start_data_process()
        time.sleep(1)
        self.dp.check_dp_status()
        self.avg_data, self.avg_num = self.dp.fetch_data_trace()
        self.dp.check_dp_status()
        self.dp.stop_data_process()


    def _set_params_fifo_multi(self):
#        self.cfg._error_check = True
#        self.dp._error_check = True
        self.ms.binwidth_s = 1 / 250e6
        self.ms.record_length_s = 1e-6
        self.ms.number_of_gates = 0
        self.cs.acq_mode = 'FIFO_MULTI'
        self.cs.trig_mode = 'EXT'
        self.ms.init_buf_size_S = 1e7
        self.dp.init_dp_params()
        self.configure(self.ms.binwidth_s, self.ms.record_length_s, self.ms.number_of_gates)


    def test_std_multi_more_reps(self, buf_length_S, notify_size_B):
        self.cs.acq_mode = 'STD_MULTI'
        self.cs.trig_mode = 'EXT'

        self.ms.binwidth_s = 1 / 250e6
        self.ms.record_length_s = 1e-6
        self.ms.number_of_gates = 0
        self.ms.init_buf_size_S = buf_length_S
        self.cs.buf_notify_size_B = notify_size_B

        self.cfg._loops = 60000
        self._start_card_with_trigger()
        self.dp.check_dp_status()

    def test_loop(self, n_loop, buf_length_S, notify_size_B):
        self.cs.acq_mode = 'STD_MULTI'
        self.cs.trig_mode = 'EXT'

        self.ms.binwidth_s = 1 / 250e6
        self.ms.record_length_s = 1e-6
        self.ms.number_of_gates = 0
        self.ms.init_buf_size_S = buf_length_S
        self.cs.buf_notify_size_B = notify_size_B
        self.cfg._loops = n_loop

    def start_loop(self):
        self._start_card_with_trigger()
        self.dp.check_dp_status()
        self.dp.start_data_process_loop(self.cfg._loops)


    def test_fifo_gate(self, buf_length_S, notify_size_B):
        self.cs.acq_mode = 'FIFO_GATE'
        self.cs.trig_mode = 'EXT'

        self.ms.binwidth_s = 1 / 250e6
        self.ms.record_length_s = 1e-6
        self.ms.number_of_gates = 0
        self.ms.init_buf_size_S = buf_length_S
        self.cs.buf_notify_size_B = notify_size_B

        self.cfg._loops = 60000
        self._start_card_with_trigger()
        self.dp.check_dp_status()

    def create_test_data(self):
        import random
        data_len = 1000
        test_data = np.zeros(1000)
        for i in range(100):
            test_data[i] = random.random()
        for i in range(100, 200):
            test_data[i] = 1000 + random.random()
        for i in range(200, 300):
            test_data[i] = random.random()
        for i in range(300, 500):
            test_data[i] = 1000 + random.random()
        for i in range(500, 600):
            test_data[i] = random.random()
        for i in range(600, 900):
            test_data[i] = 1000 + random.random()
        for i in range(900, 1000):
            test_data[i] = random.random()
        self.test_data = test_data

        return test_data

    def create_test_data_array(self, n):
        data_array = []
        for i in range(n):
            data_array = np.append(data_array, self.create_test_data())
        self.test_data_array = data_array
        return data_array




