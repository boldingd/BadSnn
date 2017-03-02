# -*- coding: utf-8 -*-
"""
Created on Thu Mar  2 03:17:04 2017

@author: boldingd
"""


class ThresholdTracker:
    """A class that counts the firing-rate for its inputs.
    Note that it's not per-input: it counts the number of spikes that it has
    received (from everything that it's connected to) and compares that to
    its high and low thresholds.
    Note that it doesn't divide by it's integration window: it's threshold-based.
    """
    
    def __init__(self, high_threshold, low_threshold, window):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

        self.window = window

        self.remaining_times = []

        self._high_state = False

        self.callbacks = []
        self.run_callbacks = False

    def step(self, dt):
        self.remaining_times = [ time - dt for time in self.remaining_times if time > dt ]

        if self._high_state:
            if len(self.remaining_times) <= self.low_threshold:
                self._high_state = False
                self.run_callbacks = True
        else:
            if len(self.remaining_times) >= self.high_threshold:
                self._high_state = True
                self.run_callbacks = True

    def exchange(self):
        if self.run_callbacks:
            self.run_callbacks = False
            for callback in self.callbacks:
                callback(self._high_state)

    def add_spike(self, magnitude):
        self.remaining_times.append(self.window)

    def add_change_callback(self, callback):
        self.callbacks.append(callback)

    def get_is_high(self):
        return self._high_state

    def get_freq(self):
        return len(self.remaining_times) / self.window


class ToggleRandomPulsar:
    """ A pulsar that is in one of two states:
    - random firing (given approximate frequency), or
    - quiet (no firing)
    """
    
    def __init__(self, magnitude, frequency):
        self.magnitude = magnitude
        self.frequency = frequency # not used after construction at present
        self.prob = 1.0 / frequency

        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False

        self._active = False

        self._become_active = False
        self._become_inactive = False
        
    def step(self, dt):
        if self._become_active == True and self._active == False:
            self._active = True
            self._spike = False
        elif self._become_inactive == True and self._active == True:
            self._active = False

        if self._active:
            if random.random() < self.prob * dt:
                self._spike = True
            
    def exchange(self):
        if self._spike:
            for s in self.synapses:
                s.add_spike(self.magnitude)
                
            for listener in self.spike_listeners:
                listener.notify_of_spike()
                
            self._spike = False
        
    def add_synapse(self, ps):
        self.synapses.append(ps)
        
    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)

    def queue_activation(self):
        self._become_active = True
        self._become_inactive = False

    def queue_inactivation(self):
        self._become_active = False
        self._become_inactive = True

    def get_is_active(self):
        return self._active


class VariableStochasticPulsar:
    """A pulsar that fires randomly, but can be switched between two firing rates.
    """
    
    def __init__(self, magnitude, low_frequency, high_frequency):
        self.magnitude = magnitude
        self.high_frequency = high_frequency # not used after construction at present
        self.low_frequency = low_frequency
        #self._prob = 1.0 / low_frequency
        self._prob = low_frequency

        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False

    def step(self, dt):
        if random.random() < self._prob * dt:
            self._spike = True
            
    def exchange(self):
        if self._spike:
            for s in self.synapses:
                s.add_spike(self.magnitude)
                
            for listener in self.spike_listeners:
                listener.notify_of_spike()
                
            self._spike = False
        
    def add_synapse(self, ps):
        self.synapses.append(ps)
        
    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)

    def queue_activation(self):
        self._prob = self.high_frequency

    def queue_inactivation(self):
        self._prob = self.low_frequency
        
        
class TogglePulsar:
    """A class that fires (deterministically) at a given firing rate.
    IT can be turned off - in which case, it doesn't fire.
    """
    
    def __init__(self, magnitude, frequency):
        self.magnitude = magnitude
        self.frequency = frequency # not used after construction at present
        self.delay = 1.0 / frequency
        self.remaining = self.delay

        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False

        self._active = False

        self._become_active = False
        self._become_inactive = False
        
    def step(self, dt):
        if self._become_active == True and self._active == False:
            self._active = True
            self._spike = False

            self.remaining = self.delay
        elif self._become_inactive == True and self._active == True:
            self._active = False

        if self._active:
            self.remaining -= dt

            if self.remaining <= 0.0:
                self.remaining = self.delay
                self._spike = True
            
    def exchange(self):
        if self._spike:
            for s in self.synapses:
                s.add_spike(self.magnitude)
                
            for listener in self.spike_listeners:
                listener.notify_of_spike()
                
            self._spike = False
        
    def add_synapse(self, ps):
        self.synapses.append(ps)
        
    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)

    def queue_activation(self):
        self._become_active = True
        self._become_inactive = False

    def queue_inactivation(self):
        self._become_active = False
        self._become_inactive = True

    def get_is_active(self):
        return self._active