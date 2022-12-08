# -*- coding: utf-8 -*-

"""
This file contains a Qudi file with sampling functions created by SaxonQ.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

import numpy as np
from qudi.logic.pulsed.sampling_functions import SamplingBase


class FourSinSum(SamplingBase):
    """
    Object representing a linear combination of four sines
    (Superposition of four sine waves; NOT normalized)
    """
    params = dict()
    params['amplitude_1'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_1'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_1'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_2'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_2'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_2'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_3'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_3'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_3'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_4'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_4'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_4'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}

    def __init__(self,
                 amplitude_1=None, frequency_1=None, phase_1=None,
                 amplitude_2=None, frequency_2=None, phase_2=None,
                 amplitude_3=None, frequency_3=None, phase_3=None,
                 amplitude_4=None, frequency_4=None, phase_4=None):
        if amplitude_1 is None:
            self.amplitude_1 = self.params['amplitude_1']['init']
        else:
            self.amplitude_1 = amplitude_1
        if frequency_1 is None:
            self.frequency_1 = self.params['frequency_1']['init']
        else:
            self.frequency_1 = frequency_1
        if phase_1 is None:
            self.phase_1 = self.params['phase_1']['init']
        else:
            self.phase_1 = phase_1

        if amplitude_2 is None:
            self.amplitude_2 = self.params['amplitude_2']['init']
        else:
            self.amplitude_2 = amplitude_2
        if frequency_2 is None:
            self.frequency_2 = self.params['frequency_2']['init']
        else:
            self.frequency_2 = frequency_2
        if phase_2 is None:
            self.phase_2 = self.params['phase_2']['init']
        else:
            self.phase_2 = phase_2

        if amplitude_3 is None:
            self.amplitude_3 = self.params['amplitude_3']['init']
        else:
            self.amplitude_3 = amplitude_3
        if frequency_3 is None:
            self.frequency_3 = self.params['frequency_3']['init']
        else:
            self.frequency_3 = frequency_3
        if phase_3 is None:
            self.phase_3 = self.params['phase_3']['init']
        else:
            self.phase_3 = phase_3
            
        if amplitude_4 is None:
            self.amplitude_4 = self.params['amplitude_4']['init']
        else:
            self.amplitude_4 = amplitude_4
        if frequency_4 is None:
            self.frequency_4 = self.params['frequency_4']['init']
        else:
            self.frequency_4 = frequency_4
        if phase_4 is None:
            self.phase_4 = self.params['phase_4']['init']
        else:
            self.phase_4 = phase_4
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase_1 / 180
        samples_arr = self._get_sine(time_array, self.amplitude_1, self.frequency_1, phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase_2 / 180
        samples_arr += self._get_sine(time_array, self.amplitude_2, self.frequency_2, phase_rad)

        # Third sine wave (add on sum of first and second)
        phase_rad = np.pi * self.phase_3 / 180
        samples_arr += self._get_sine(time_array, self.amplitude_3, self.frequency_3, phase_rad)
        
        # Fourth sine wave (add on sum of first, second and third)
        phase_rad = np.pi * self.phase_4 / 180
        samples_arr += self._get_sine(time_array, self.amplitude_4, self.frequency_4, phase_rad)
        return samples_arr
    
        
    
        
        
    
    
    