'''
Created on May 2, 2014

@author: sdejonckheere
'''
from finale import settings

import pyopencl as cl

import numpy
from finale.settings import RESOURCES_MAIN_PATH
import os
import logging
from seq_common.utils import dates

LOGGER = logging.getLogger(__name__)

computers = {}

def get_tracks_computer():
    if not computers.has_key('track_computer'):
        if settings.OPENCL_ENABLE:
            computers['track_computer'] = CLTracksComputer()
        else:
            computers['track_computer'] = NativeTracksComputer()
    return computers['track_computer']

def get_previous_date(current_date, frequency):
    # Adjust with frequency reference
    if frequency.identifier=='FREQ_DAILY':
        return dates.AddDay(current_date, -1)
    if frequency.identifier=='FREQ_WEEKLY':
        return dates.AddDay(current_date, -7)
    if frequency.identifier=='FREQ_MONTHLY':
        return dates.AddDay(dates.GetStartOfMonth(current_date), -1)
    if frequency.identifier=='FREQ_QUARTERLY':
        return dates.GetEndOfMonth(dates.AddQuarter(current_date, -1))
    if frequency.identifier=='FREQ_SEMESTERLY':
        return dates.GetEndOfMonth(dates.AddQuarter(current_date, -2))
    if frequency.identifier=='FREQ_ANNUALLY':
        return dates.GetEndOfMonth(dates.AddYear(current_date, -1))
    if frequency.identifier=='FREQ_EVERY_2_YEARS':
        return dates.GetEndOfMonth(dates.AddYear(current_date, -2))
    if frequency.identifier=='FREQ_EVERY_3_YEARS':
        return dates.GetEndOfMonth(dates.AddYear(current_date, -3))
    return current_date

def get_next_date(current_date, frequency):
    # Adjust with frequency reference
    if frequency.identifier=='FREQ_DAILY':
        return dates.AddDay(current_date, 1)
    if frequency.identifier=='FREQ_WEEKLY':
        return dates.AddDay(current_date, 7)
    if frequency.identifier=='FREQ_MONTHLY':
        return dates.GetEndOfMonth(dates.AddDay(dates.GetEndOfMonth(current_date), 1))
    if frequency.identifier=='FREQ_QUARTERLY':
        return dates.GetEndOfMonth(dates.AddQuarter(current_date, 1))
    if frequency.identifier=='FREQ_SEMESTERLY':
        return dates.GetEndOfMonth(dates.AddQuarter(current_date, 2))
    if frequency.identifier=='FREQ_ANNUALLY':
        return dates.GetEndOfMonth(dates.AddYear(current_date, 1))
    if frequency.identifier=='FREQ_EVERY_2_YEARS':
        return dates.GetEndOfMonth(dates.AddYear(current_date, 2))
    if frequency.identifier=='FREQ_EVERY_3_YEARS':
        return dates.GetEndOfMonth(dates.AddYear(current_date, 3))
    return current_date

class CLTracksComputer():
    platform = None
    device = None
    context = None
    queue = None
    data_type = numpy.float32
    memory_flags = cl.mem_flags
    program = ""
    
    def __init__(self):
        self.platform = cl.get_platforms()[settings.OPENCL_PLATFORM]
        self.device = self.platform.get_devices()[settings.OPENCL_DEVICE]
        self.context = cl.Context([self.device])
        with open(os.path.join(RESOURCES_MAIN_PATH, 'TracksComputer.cl'),'r') as program_file:
            for line in program_file:
                self.program += line
        self.program = self.program.replace('ACTIVE_PRECISION', 'double' if settings.OPENCL_DOUBLE_PRECISION_ENABLE else 'float')
        self.program = cl.Program(self.context, self.program).build()
        self.queue = cl.CommandQueue(self.context)
        self.data_type = numpy.float64 if settings.OPENCL_DOUBLE_PRECISION_ENABLE else numpy.float32
        LOGGER.info("Computation will be executed by [" + str(self.platform) + "," + str(self.device) + "]")
    
    def compute_performances(self, ordered_track_values):
        values = numpy.asarray(ordered_track_values, self.data_type)
        buffer_values = cl.Buffer(self.context, self.memory_flags.READ_ONLY | self.memory_flags.COPY_HOST_PTR, hostbuf=values)
        performances = numpy.zeros(len(ordered_track_values), self.data_type)
        buffer_results = cl.Buffer(self.context, self.memory_flags.WRITE_ONLY, performances.nbytes)
        self.program.performances(self.queue, performances.shape, None, buffer_values, buffer_results)
        cl.enqueue_copy(self.queue, performances, buffer_results)
        return performances
    
class NativeTracksComputer():
    
    def __init__(self):
        LOGGER.info("Computation will be executed using the CPU")
        
    def compute_performances(self, ordered_track_values):
        results = [0.0]
        for index in range(1, len(ordered_track_values)):
            if ordered_track_values[index-1]!=0.0:
                results.append((ordered_track_values[index]/ordered_track_values[index-1]) - 1.0)
            else:
                results.append(None)
        return results
            
            