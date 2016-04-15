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
            delta += current.get_current() * dt # should probably be per unit time
            
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
        
class StdpFunction:
    def __init__(self, tau_p, A_p, tau_n = None, A_n = None):
        self.tau_p = tau_p
        self.A_p = A_p
        
        if tau_n is None:
            self.tau_n = tau_p
        else:
            self.tau_n = tau_n
            
        if A_n is None:
            self.A_n = A_p
        else:
            self.A_n = A_n
            
    def __call__(self, gap): # post- pre => positive should strengthen
        if gap > 0.0:
            return self.A_p * math.exp(-1.0 * gap / self.tau_p)
        else:
            return -1.0 * self.A_n * math.exp(gap / self.tau_n)

# TODO: finish updating this to work with Step/Exchange design
#       add_spike and notify_of_spike should only occur during exchange step
#       so they'll mark the total change and apply during compute
class StdpSynapse:
    def __init__(self, delay, efficiency, min_efficiency, max_efficiency):
        self.delay = delay
        self.min_efficiency = min_efficiency
        self.max_efficiency = max_efficiency
        
        self.efficiency = efficiency
        
        self.M = 0.0
        self.A_m = 0.015
        self.tau_m = 0.0025
        
        self.P = 0.0
        self.A_p = 0.015
        self.tau_p = 0.0025
        
        self.waiting_spikes = []
        self.outgoing_spikes = []
        
        self.targets = []
        
        self.efficiency_update = 0.0        
        
    def add_spike(self, magnitude):
        # every time we receive a spike, add A+ to P
        self.P += self.A_p

        # then (?) schedule a decrement by M*g_max (M should be negative or 0)        
        self.efficiency_update += self.M * self.max_efficiency
            
        ds = DelayedSpike(self.delay, magnitude)
        
        self.waiting_spikes.append(ds)
    
    def add_target(self, target):
        self.targets.append(target)
        
    def get_sample(self):
        return self.efficiency
        
    def notify_of_spike(self):
        # every time the post-synaptic fires, subtract A- from M
        self.M -= self.A_m
        
        self.efficiency_update += self.P * self.max_efficiency
        
    def prepare(self):
        # apply efficiency change from last cycle before step / exchange
        if self.efficiency_update != 0.0:
            self.efficiency += self.efficiency_update
            
            # clip to allowed range
            if self.efficiency > self.max_efficiency:
                self.efficiency = self.max_efficiency
            elif self.efficiency < self.min_efficiency:
                self.efficiency = self.min_efficiency
                
            self.efficiency_update = 0.0
            
    def step(self, dt):
        # M and P exponentially decay to 0
        delta_M = -1.0 * self.M * (dt / self.tau_m)
        self.M += delta_M
        
        delta_P = -1.0 * self.P * (dt / self.tau_p)
        self.P += delta_P
        
        # spike, as basic delayed neuron
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

class Pulsar:
    def __init__(self, magnitude, delay):
        self.magnitude = magnitude
        self.delay = delay
        self.remaining = delay

        self.synapses = []
        
        self.spike = False
        
    def step(self, dt):
        self.remaining -= dt

        if self.remaining <= 0.0:
            self.remaining = self.delay
            self.spike = True
            
    def exchange(self):
        if self.spike == True:
            for s in self.synapses:
                s.add_spike(self.magnitude)
                
            self.spike = False
        
    def add_synapse(self, ps):
        self.synapses.append(ps)
        
def get_pulsar_for_frequency(power, frequency):
    """Construct a pulsar with a given power and frequency.
    Useful because the most common use-case is an array of pulsars of constant power at varying freuqencies.
    power is given in units-per-whole-tick (units-per-second)
    frequency is given in pulses-per-whole-tick (hertz)
    this,
    magnitude = power / frequency
    delay = 1.0 / frequency
    """
    magnitude = power / frequency
    delay = 1.0 / frequency
    
    return Pulsar(magnitude, delay)
        
class NaiveRandomSpiker:
    def __init__(self, magnitude, freq):
        self.magnitude = magnitude
        self.freq = freq
        
        self.synapses = []
        
        self._gap = random.uniform(0.0, 2.0 / freq)
        
        self.spike = False
        
    def step(self, dt):
        self._gap -= dt
        
        if self._gap <= 0.0:
            self.spike = True
            self._gap = random.uniform(0.0, 2.0 / self.freq)
            
    def exchange(self):
        if self.spike == True:
            for synapse in self.synapses:
                synapse.add_spike(self.magnitude)
            
            self.spike = False
        
    def add_synapse(self, ps):
        self.synapses.append(ps)

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
    def __init__(self, source, interval, name=None):
        self.source = source
        self.interval = interval

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

class SinusoidSource:
    def __init__(self, frequency, amplitude):
        self.frequency = frequency
        self.freq_mult = 2.0 * 3.14159 * frequency
        self.amplitude = amplitude

        self.time = 0.0

    def step(self, dt):
        self.time += dt

    def get_current(self):
        return self.amplitude * math.sin(self.freq_mult * self.time)

    def get_sample(self):
        return self.get_current()

class SumOfSines:
    def __init__(self):
        self.sinusoids = []

    def step(self, dt):
        for sine in self.sinusoids:
            sine.step(dt)

    def get_current(self):
        sum = 0.0

        for sine in self.sinusoids:
            sum += sine.get_current()

        return sum

    def get_sample(self):
        return self.get_current()

    def add_sinusoid(self, frequency, amplitude):
        s = SinusoidSource(frequency, amplitude)
        
        self.sinusoids.append(s)

class Delayer:
    def __init__(self, entity, delay):
        self.entity = entity
        self.delay = delay
        
    def step(self, dt):
        if self.delay > 0.0:
            self.delay -= dt
        else:
            self.entity.step(dt)
            
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
            try:
                entity.prepare()
            except AttributeError:
                pass
            
            entity.step(step)
            
            # call entity.exchange() if it exists
            try:
                entity.exchange()
            except AttributeError:
                pass
            
        time += step

class _SimulationManagerIterator:
    def __init__(self, manager):
        self.manager = manager
        
    def __next__(self):
        pass # todo - got lazy
        
class SimulationmManager:
    def __init__(self):
        self.independant_entities = list()
        self.entity_sources = list()
        
    def __iter__(self):
        return _SimulationManagerIterator(self)
        
    