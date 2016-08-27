import math
import random

import SnnBase

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
            
        ds = SnnBase.DelayedSpike(self.delay, magnitude) # TODO: inter-module coupling for trivial class
        
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
                
    @staticmethod
    def connect(source, target, delay, efficiency, min_efficiency, max_efficiency):
        s = StdpSynapse(delay, efficiency, min_efficiency, max_efficiency)
        
        s.add_target(target)
        source.add_synapse(s)
        
        target.add_spike_listener(s)
        
        return s

