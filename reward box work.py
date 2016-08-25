import SnnBase

import math
import random

class SinusoidalDrivingFunction:
    def __init__(self, frequency=1.0, bias=0.0, magnitude=0.1, phase=0.0):
        if phase < 0.0 or phase > 2 * 3.14159:
            raise Exception("Invalid phase")

        self.frequency = frequency
        self.bias = bias
        self.magnitude = magnitude
        self.multiplier = 2.0 * 3.14159 * frequency
        self.phase = phase #
        
        self.t = 0.0

    def step(self, dt):
        self.t += dt

    def __call__(self):
        return self.bias + math.sin( (self.t + self.phase) * self.multiplier) * self.magnitude

    def get_sample(self):
        return self()
        

#class DrivenPoissonSpiker:
#    def __init__(self, magnitude, frequency, driving_function):
#        self.magnitude = magnitude
#        self.frequency = frequency
#
#        self.driving_function = driving_function
#        
#        self.synapses = []
#        
#        self.spike_listeners = []
#        
#        self._spike = False
#        
#    def step(self, dt):
#        u = random.uniform(0.0, 1.0)
#        #u += self.driving_function()
#        u -= self.driving_function() # TODO: express more elegantly
#        if u <= dt * self.frequency:
#            self._spike = True
#            
#    def exchange(self):
#        if self._spike:
#            for synapse in self.synapses:
#                synapse.add_spike(self.magnitude)
#                
#            for listener in self.spike_listeners:
#                listener.notify_of_spike()
#                
#            self._spike = False
#            
#    def add_synapse(self, syn):
#        self.synapses.append(syn)
#        
#    def add_spike_listener(self, listener):
#        self.spike_listeners.append(listener)


class DrivenPoissonSpiker:
    def __init__(self, magnitude, alpha, threshold, driving_function):
        self.magnitude = magnitude
        self.alpha = alpha
        self.threshold = threshold

        self.driving_function = driving_function
        
        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False
        
    def step(self, dt):
        u = random.uniform(0.0, 1.0)

        r = self.alpha * (self.driving_function() - self.threshold) # effective freq is function of driving function

        if u <= dt * r:
            self._spike = True
            
    def exchange(self):
        if self._spike:
            for synapse in self.synapses:
                synapse.add_spike(self.magnitude)
                
            for listener in self.spike_listeners:
                listener.notify_of_spike()
                
            self._spike = False
            
    def add_synapse(self, syn):
        self.synapses.append(syn)
        
    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)


class StateLogger:
    def __init__(self, name, box):
        self.name = name
        self.box = box
        self.last_state = box._high_state

        self.t = 0.0

        self.history = [ ]

    def step(self, dt):
        self.t += dt

    def exchange(self):
        # should get state from other objects in exchange

        if self.box._high_state != self.last_state:
            self.history.append( (self.t, self.box._high_state) )
            self.last_state = self.box._high_state

    def write_log(self):
        with open(self.name + ".dat", "w") as ofile:
            for change in self.history:
                if change[1]:
                    ofile.write("{}: became HIGH\n".format(change[0]))
                else:
                    ofile.write("{}: became  LOW\n".format(change[0]))

class RewardBox:
    def __init__(self, high_threshold, low_threshold, window):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

        self.window = window

        self.remaining_times = []

        self._high_state = False

        self.callbacks = []
        self.run_callbacks = False

    # assume we'll get spikes during exchange
    # prepare: arrived -> waiting, waiting -= time
    #   can I just cram arrived spikes in at full time?  I think so
    # step: change state (?)
    # exchange: send reward

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

class SymbolTracker:
    pass

class CallbackManager:
    def __init__(self, freq):
        self.t = 0.0
        self.freq = freq
        self.wait = 1.0 / freq

        self.run_callbacks = False
        self.callbacks = []

    def step(self, dt):
        self.t += dt
        self.wait -= dt

        if self.wait <= 0.0:
            self.wait = 1.0 / self.freq
            self.run_callbacks = True

    def exchange(self):
        if self.run_callbacks:
            self.run_callbacks = False

            for callback in self.callbacks:
                callback(self.t) # note: if callback causes an AttributeError, that will get suppressed later

    def add_callback(self, callback):
        self.callbacks.append(callback)

class Clock:
    def __init__(self):
        self.t = 0.0

    def step(self, dt):
        self.t += dt

clock = Clock()

#driver = SinusoidalDrivingFunction(0.5)
#pspiker = DrivenPoissonSpiker(magnitude=1.0, frequency=5.0, driving_function=driver)

driver = SinusoidalDrivingFunction(frequency=0.5, bias=0.6, magnitude=0.4, phase=0.0)
pspiker = DrivenPoissonSpiker(magnitude=1.0, alpha=15.0, threshold=0.0, driving_function=driver)

rbox = RewardBox(high_threshold=6, low_threshold=4, window=0.4)
#rbox.add_change_callback(lambda new_value: print("{}: became {}".format(clock.t, new_value)))

logger = StateLogger("rbox", rbox)

syn = SnnBase.Synapse.connect(pspiker, rbox)

calls = CallbackManager(freq=100.0)


states = list()
def get_record(time):
    sin = driver()
    count = len(rbox.remaining_times)
    if rbox._high_state:
        reward = 1.0
    else:
        reward = 0.0

    states.append( (time, sin, count, reward) )
calls.add_callback(get_record)


entities = [clock, driver, pspiker, rbox, syn, logger, calls]
SnnBase.run_simulation(10.0, 1 / 2000, entities)

logger.write_log()

with open("states.dat", "w") as ofile:
    for s in states:
        ofile.write( "{} {} {} {}\n".format(s[0], s[1], s[2], s[3]) )

