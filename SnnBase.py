import math

import random

# TODO: I think when a spike arrives could still be order dependant, it could still take one step or two.
#       going to have to deliver queued spikes during the prepare step

class SnnError(Exception):
    pass

class SpikingNeuron:
    def __init__(self, threshold, magnitude, leak_eql, leak_tau):
        self.threshold = threshold
        self.magnitude = magnitude

        self.eql = leak_eql
        self.tau = leak_tau
        self.tau_mult = 1.0 / leak_tau

        self.currents = []

        self.charge = self.eql

        self.synapses = []

        self.spike_listeners = []
        
        self.received_spikes = []
        
        self.spike = False
            
    def step(self, dt):
        delta = -1.0 * (self.charge - self.eql) * (self.tau_mult) * dt
        
        for current in self.currents:
            delta += (current.eql - self.charge) * dt * current.conductance
            
        for spike in self.received_spikes:
            delta += spike
        self.received_spikes = []
        
        self.charge += delta

        if self.charge >= self.threshold:
            self.charge = self.eql
            self.spike = True
    
    def exchange(self):
        if self.spike == True:            
            for ps in self.synapses:
                ps.add_spike(self.magnitude)

            for listener in self.spike_listeners:
                listener.notify_of_spike()
                
            self.spike = False

    def add_spike(self, magnitude):
        self.received_spikes.append(magnitude)

    def add_synapse(self, synapse):
        self.synapses.append(synapse)

    def add_current(self, current):
        self.currents.append(current)

    # order-dependant, value will be different before and after step()
    def get_charge(self):
        return self.charge

    def get_sample(self):
        return self.charge

    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)

class DelayedSpike:
    def __init__(self, delay, magnitude):
        self.remaining_delay = delay
        self.magnitude = magnitude

class Synapse:
    def __init__(self, delay, efficiency=1.0):
        self.delay = delay
        self.efficiency = efficiency

        self.waiting_spikes = []
        self.outgoing_spikes = []

        self.targets = []

    def step(self, dt):
        # probably some clever list-comprehending could do this more concisely
        temp_spikes = self.waiting_spikes
        self.waiting_spikes = []
        self.outgoing_spikes = []

        for spike in temp_spikes:
            spike.remaining_delay -= dt
            
            if spike.remaining_delay <= 0.0:
                self.outgoing_spikes.append(spike)
            else:
                self.waiting_spikes.append(spike)

    def exchange(self):
        for s in self.outgoing_spikes:
            for t in self.targets:
                t.add_spike(self.efficiency * s.magnitude)

    def add_spike(self, magnitude):
        ds = DelayedSpike(self.delay, magnitude)

        self.waiting_spikes.append(ds)

    def add_target(self, target):
        self.targets.append(target)
        
    @staticmethod
    def connect(source, target, delay=0.0, efficiency=1.0):
        s = Synapse(delay, efficiency)
        s.add_target(target)
        source.add_synapse(s)
        
        return s
        
class Pulsar:
    def __init__(self, magnitude, frequency):
        self.magnitude = magnitude
        self.frequency = frequency # not used after construction at present
        self.delay = 1.0 / frequency
        self.remaining = self.delay

        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False
        
    def step(self, dt):
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

class NaiveRandomSpiker:
    def __init__(self, magnitude, freq):
        self.magnitude = magnitude
        self.freq = freq
        
        self.synapses = []
        
        self.spike_listeners = []
        
        self._gap = random.uniform(0.0, 2.0 / freq)
        
        self._spike = False
        
    def step(self, dt):
        self._gap -= dt
        
        if self._gap <= 0.0:
            self._spike = True
            self._gap = random.uniform(0.0, 2.0 / self.freq)
            
    def exchange(self):
        if self._spike == True:
            for synapse in self.synapses:
                synapse.add_spike(self.magnitude)
                
            for listener in self.spike_listeners:
                listener.notify_of_spike()
            
            self._spike = False
        
    def add_synapse(self, ps):
        self.synapses.append(ps)
        
    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)
        
class PoissonSpiker:
    # NB: possibly almost the same as the NaiveRandomSpiker

    def __init__(self, magnitude, frequency):
        self.magnitude = magnitude
        self.frequency = frequency
        
        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False
        
    def step(self, dt):
        u = random.uniform(0.0, 1.0)
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

class DrivenPoissonSpiker:
    # driving function should be an object with a __call__ method
    # __call__ should have no parameters (it won't be given any)
    # if it needs to be stepped, it should be stepped seperately
    # TODO: evaluate how good an idea this really is
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

# TODO: there's an order-dependance if this thing steps before or after Synapses
class Current:
    """A trivial, constant current
    has a step, because other currents might need to step
    """
    def __init__(self, eql, conductance):
        self.eql = eql
        self.conductance = conductance

    def step(self, dt):
        pass

class SpikeRecord:
    def __init__(self, time, magnitude):
        self.time = time
        self.magnitude = magnitude

class Counter:
    def __init__(self, name=None):
        self.time = 0.0

        self.spikes = []

        self.name = name

    def step(self, dt):
        self.time += dt

    def add_spike(self, magnitude):
        sr = SpikeRecord(self.time, magnitude)
        self.spikes.append(sr)
        
    def notify_of_spike(self):
        sr = SpikeRecord(self.time, None) # no magnitude when using "spike-listener protocol"
        self.spikes.append(sr)

    def dump_records(self):
        if self.name is not None:
            print("spike record for counter {}".format(self.name))

        for record in self.spikes:
            if record.magnitude is None:
                print("t{}:  spike".format(record.time))
            else:
                print("t{}:  {}mV".format(record.time, record.magnitude))

    def write_records(self, ostream):
        for record in self.spikes:
            if record.magnitude is None:
                ostream.write("t{}:  spike\n".format(record.time))
            else:
                ostream.write("t{}:  {}mv\n".format(record.time, record.magnitude))

    def report(self, fname=None):
        # fname overrides self.name when picking file name
        out_path = fname
        if out_path is None:
            if self.name is not None:
                out_path = self.name + ".dat"
            else:
                raise SnnError("Could not pick a unique file name")

        with open(out_path, "w") as ofile:
            self.write_records(ofile)

class Sample:
    def __init__(self, time, charge):
        self.time = time
        self.charge = charge

class Sampler:
    def __init__(self, source, frequency, name=None):
        self.source = source
        #self.frequency = frequency
        self.interval = 1.0 / frequency

        self.remaining = 0.0 # have samplers record on first tick

        self.samples = []

        self.time = 0.0

        self.name = name
        
        self.sample = False

    def step(self, dt):
        self.time += dt

        self.remaining -= dt

        if self.remaining <= 0.0:
            self.remaining = self.interval
            self.sample = True
            
    def exchange(self):
        if self.sample == True:
            s = Sample(self.time, self.source.get_sample())
            self.samples.append(s)
            
            self.sample = False

    def write_samples(self, ostream):
        for sample in self.samples:
            ostream.write("{} {}\n".format(sample.time, sample.charge))

    def report(self, fname=None):
        # fname overrides self.name when picking file name
        out_path = fname
        if out_path is None:
            if self.name is not None:
                out_path = self.name + ".dat"
            else:
                raise SnnError("Could not pick a unique file name")

        with open(out_path, "w") as ofile:
            self.write_samples(ofile)

## Easy enough to implement if useful
#class SinusoidSource:
#    def __init__(self, frequency, amplitude):
#        self.frequency = frequency
#        self.freq_mult = 2.0 * 3.14159 * frequency
#        self.amplitude = amplitude
#
#        self.time = 0.0
#
#    def step(self, dt):
#        self.time += dt
#
#    def get_current(self):
#        return self.amplitude * math.sin(self.freq_mult * self.time)
#
#    def get_sample(self):
#        return self.get_current()
#
#class SumOfSines:
#    def __init__(self):
#        self.sinusoids = []
#
#    def step(self, dt):
#        for sine in self.sinusoids:
#            sine.step(dt)
#
#    def get_current(self):
#        sum = 0.0
#
#        for sine in self.sinusoids:
#            sum += sine.get_current()
#
#        return sum
#
#    def get_sample(self):
#        return self.get_current()
#
#    def add_sinusoid(self, frequency, amplitude):
#        s = SinusoidSource(frequency, amplitude)
#        
#        self.sinusoids.append(s)

class Delayer:
    def __init__(self, entity, delay):
        self.entity = entity
        self.delay = delay
        
    def step(self, dt):
        if self.delay > 0.0:
            self.delay -= dt
        else:
            self.entity.step(dt)

## Moved to Utilities
# class CallbackManager:
#     def __init__(self, freq):
#         self.t = 0.0
#         self.freq = freq
#         self.wait = 1.0 / freq

#         self.run_callbacks = False
#         self.callbacks = []

#     def step(self, dt):
#         self.t += dt
#         self.wait -= dt

#         if self.wait <= 0.0:
#             self.wait = 1.0 / self.freq
#             self.run_callbacks = True

#     def exchange(self):
#         if self.run_callbacks:
#             self.run_callbacks = False

#             for callback in self.callbacks:
#                 callback(self.t)

#     def add_callback(self, callback):
#         self.callbacks.append(callback)
            
def linspace(minimum, maximum, count):
    """a lazy reimplementation of linspace
    because I often need linspace but I'm too lazy to import a module that would provide it.
    NB this version includes both end-points, which might make the step not what you expect.
    """
    
    if maximum <= minimum:
        raise ValueError("minimum must be less than maximum")
        
    if count <= 1:
        raise ValueError("count must be at least 2")
    
    step = (maximum - minimum) / (count - 1) # step should be a float
    
    return [ minimum + step * x for x in range(count)]
    
def run_simulation(stop_time, step, entities):
    time = 0.0
    
    while time < stop_time:
        for entity in entities:
            
            # call entity.compute() if it exists
#            try:
#                entity.prepare()
#            except AttributeError:
#                pass
#

            if hasattr(entity, "prepare") and callable(entity.prepare):
                entity.prepare()
            
            entity.step(step)
            
            # call entity.exchange() if it exists
#            try:
#                entity.exchange()
#            except AttributeError:
#                pass

            if hasattr(entity, "exchange") and callable(entity.exchange):
                entity.exchange()

            # TODO: this fails if exchange raises an attribute error!
            # and it did so, one too many times
            
        time += step

#class _SimulationManagerIterator:
#    def __init__(self, manager):
#        self.manager = manager
#        
#    def __next__(self):
#        pass # todo - got lazy
#        
#class SimulationmManager:
#    def __init__(self):
#        self.independant_entities = list()
#        self.entity_sources = list()
#        
#    def __iter__(self):
#        return _SimulationManagerIterator(self)
        
    
