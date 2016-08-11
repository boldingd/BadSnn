import SnnBase

import math
import random

class SinusoidalDrivingFunction:
    def __init__(self, frequency=1.0, bias=0.0, magnitude=0.1):
        self.frequency = frequency
        self.bias = bias
        self.magnitude = magnitude
        self.multiplier = 2.0 * 3.14159 * frequency
        
        self.t = 0.0

    def step(self, dt):
        self.t += dt

    def __call__(self):
        return self.bias + math.sin(self.t * self.multiplier) * self.magnitude
        

class DrivenPoissonSpiker:
    def __init__(self, magnitude, frequency, driving_function):
        self.magnitude = magnitude
        self.frequency = frequency

        self.driving_function = driving_function
        
        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False
        
    def step(self, dt):
        u = random.uniform(0.0, 1.0)
        u += self.driving_function()
        if u <= dt * self.frequency:
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

        if self.last_state is None:
            self.last_state = box._high_state
        else:
            if box._high_state != self.last_state:
                self.history.append( (self.t, box._high_state) )
                self.last_state = box._high_state

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

    # assume we'll get spikes during exchange
    # prepare: arrived -> waiting, waiting -= time
    #   can I just cram arrived spikes in at full time?  I think so
    # step: change state (?)
    # exchange: send reward

#    def prepare(self):
#        pass

    def step(self, dt):
        self.remaining_times = [ time - dt for time in self.remaining_times if time > dt ]

        #print(len(self.remaining_times))

        if self._high_state:
            if len(self.remaining_times) <= self.low_threshold:
                self._high_state = False
        else:
            if len(self.remaining_times) >= self.high_threshold:
                self._high_state = True

        print(self._high_state)

#    def exchange(self):
#        pass

    def add_spike(self, magnitude):
        self.remaining_times.append(self.window)


driver = SinusoidalDrivingFunction(0.5)
pspiker = DrivenPoissonSpiker(magnitude=1.0, frequency=5.0, driving_function=driver)
rbox = RewardBox(high_threshold=3, low_threshold=7, window=0.5)

logger = StateLogger("rbox", rbox)

syn = SnnBase.Synapse.connect(pspiker, rbox)

entities = [driver, pspiker, rbox, syn]
SnnBase.run_simulation(10.0, 1 / 1000, entities)

logger.write_log()


