import stdp

#class SymmetricStdpSynapse:
#    def __init__(self, delay, efficiency, min_efficiency, max_efficiency, window):
#        self.delay = delay
#        self.min_efficiency = min_efficiency
#        self.max_efficiency = max_efficiency
#        
#        self.efficiency = efficiency
#        
#        self.window = window
#
#        self.T = None
#        
#        self.waiting_spikes = []
#        self.outgoing_spikes = []
#        
#        self.targets = []
#        
#        self.efficiency_update = 0.0        
#        
#    def add_spike(self, magnitude):
#        self.efficiency_update += (1.0 / math.cosh(self.T)) - 0.5 # sech(x) - 0.5
#        self.T += self.A_t
#            
#        ds = SnnBase.DelayedSpike(self.delay, magnitude)
#        
#        self.waiting_spikes.append(ds)
#    
#    def add_target(self, target):
#        self.targets.append(target)
#        
#    def get_sample(self):
#        return self.efficiency
#        
#    def notify_of_spike(self):
#        self.efficiency_update += (1.0 / math.cosh(self.T)) - 0.5 # sech(x) - 0.5
#        
#    def prepare(self):
#        # apply efficiency change from last cycle before step / exchange
#        if self.efficiency_update != 0.0:
#            self.efficiency += self.efficiency_update
#            
#            # clip to allowed range
#            if self.efficiency > self.max_efficiency:
#                self.efficiency = self.max_efficiency
#            elif self.efficiency < self.min_efficiency:
#                self.efficiency = self.min_efficiency
#                
#            self.efficiency_update = 0.0
#            
#    def step(self, dt):        
#        # M and P exponentially decay to 0
#        delta_T = -1.0 * self.T * (dt / self.tau_t)
#        self.T += delta_T
#        
#        # spike, as basic delayed neuron
#        temp_spikes = self.waiting_spikes
#        self.waiting_spikes = []
#        self.outgoing_spikes = []
#
#        for spike in temp_spikes:
#            spike.remaining_delay -= dt
#            
#            if spike.remaining_delay <= 0.0:
#                self.outgoing_spikes.append(spike)
#            else:
#                self.waiting_spikes.append(spike)
#                
#    def exchange(self):
#        for s in self.outgoing_spikes:
#            for t in self.targets:
#                t.add_spike(self.efficiency * s.magnitude)
#                
#    @staticmethod
#    def connect(source, target, delay, efficiency, min_efficiency, max_efficiency):
#        s = InhibitoryStdpSynapse(delay, efficiency, min_efficiency, max_efficiency)
#        
#        s.add_target(target)
#        source.add_synapse(s)
#        
#        target.add_spike_listener(s)
#        
#        return s


class TogglePulsar:
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

        if self.active:
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


class RateTracker:
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


class Controller:
    def __init__(self):
        pass


ex_1 = SpikingNeuron(threshold=50.0, magnitude=10.0, leak_eql=0.0, leak_tau=0.5)
ex_2 = SpikingNeuron(threshold=50.0, magnitude=10.0, leak_eql=0.0, leak_tau=0.5)
inh  = SpikingNeuron(threshold=50.0, magnitude=10.0, leak_eql=0.0, leak_tau=0.5)

rt_1 = RateTracker(high_threshold=10, low_threshold=5, window=0.5)
rt_2 = RateTracker(high_threshold=10, low_threshold=5, window=0.5)

t_1 = TogglePulser(magnitude=10.0, frequency=10.0)
t_2 = TogglePulser(magnitude=10.0, frequency=10.0)




