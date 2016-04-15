# -*- coding: utf-8 -*-
"""
Created on Mon Mar 28 20:20:06 2016

@author: boldingd
"""

import SnnBase


class DopamineStdpSynapse:
    def __init__(self, delay, efficiency, min_efficiency, max_efficiency):
        self.delay = delay
        self.min_efficiency = min_efficiency
        self.max_efficiency = max_efficiency
        
        self.efficiency = efficiency
        
        self.M = 0.0 # LTD term
        self.A_m = 0.02 # LTD slightly dominates in Izhikevitch model
        self.tau_m = 0.0035
        
        self.P = 0.0 # LTP term
        self.A_p = 0.015
        self.tau_p = 0.0025
        
        self.waiting_spikes = []
        self.outgoing_spikes = []
        self.targets = []
        
        self.c = 0.0 # dopamine tag variable
        self.tau_c = 15.0 # dopamine time-dynamics are __slow__
        
    def add_spike(self, magnitude):
        # every time we receive a spike, add A+ to P
        self.P += self.A_p
        
        # apply to tag (c) rather than efficiency directly
        self.c += self.M * self.max_efficiency
            
        ds = SnnBase.DelayedSpike(self.delay, magnitude)
        
        self.waiting_spikes.append(ds)
    
    def add_target(self, target):
        self.targets.append(target)
        
    def get_sample(self):
        return self.efficiency
        
    def notify_of_spike(self):
        # every time the post-synaptic fires, subtract A- from M
        self.M -= self.A_m
        
        # apply to tag (c) rather than efficiency directly
        self.c += self.P * self.max_efficiency
        
    def step(self, dt):
        # M, P and c exponentially decay to 0
        delta_M = -1.0 * self.M * (dt / self.tau_m)
        self.M += delta_M
        
        delta_P = -1.0 * self.P * (dt / self.tau_p)
        self.P += delta_P
        
        delta_c = -1.0 * self.c * (dt / self.tau_c)
        self.c += delta_c
        
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
                
    def reward(self):
        # apply tag
        self.efficiency += self.c
        
        # clamp to allowed range
        if self.efficiency > self.max_efficiency:
            self.efficiency = self.max_efficiency
        elif self.efficiency < self.min_efficiency:
            self.efficiency = self.min_efficiency
                
# using "integrate-and-reward" discrete model
class DopamineManager:
    def __init__(self, equilibrium, tau, threshold):
        self.equilibrium = equilibrium
        self.level = equilibrium
        self.tau = tau
        self.threshold = threshold
        
        self.reward_listeners = []
        self.reward_pending = False

    def add_dopamine(self, ammount):
        self.level += ammount
        
    def step(self, dt):
        if self.level >= self.threshold:
            self.reward_pending = True
            self.level = self.equilibrium
        else: # decay exponentially
            delta = (self.equilibrium - self.level) * (dt / self.tau)
            self.level += delta
            
    def exchange(self):
        if self.reward_pending == True:
            self.notify_reward_listeners()
            self.reward_pending = False

    def get_sample(self):
        return self.level
        
    def add_reward_listener(self, listener):
        self.reward_listeners.append(listener)
        
    def notify_reward_listeners(self):
        for listener in self.reward_listeners:
            listener.reward()


#class DopamineStdpSynapse:
#    def __init__(self, delay, efficiency, min_efficiency, max_efficiency):
#        self.delay = delay
#        self.min_efficiency = min_efficiency
#        self.max_efficiency = max_efficiency
#        
#        self.efficiency = efficiency
#        
#        self.M = 0.0 # LTD term
#        self.A_m = 0.02 # LTD slightly dominates in Izhikevitch model
#        self.tau_m = 0.0035
#        
#        self.P = 0.0 # LTP term
#        self.A_p = 0.015
#        self.tau_p = 0.0025
#        
#        self.waiting_spikes = []
#        self.outgoing_spikes = []
#        self.targets = []
#        
#        self.c = 0.0 # dopamine tag variable
#        self.tau_c = 15.0 # dopamine time-dynamics are __slow__
#        
#        self.dopamine_level = 0.0        
#        
#    def add_spike(self, magnitude):
#        # every time we receive a spike, add A+ to P
#        self.P += self.A_p
#        
#        # apply to tag (c) rather than efficiency directly
#        self.c += self.M * self.max_efficiency
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
#        # every time the post-synaptic fires, subtract A- from M
#        self.M -= self.A_m
#        
#        # apply to tag (c) rather than efficiency directly
#        self.c += self.P * self.max_efficiency
#        
#    def prepare(self):
#        self.efficiency += self.c * 
#
#    def step(self, dt):
#        # M, P and c exponentially decay to 0
#        delta_M = -1.0 * self.M * (dt / self.tau_m)
#        self.M += delta_M
#        
#        delta_P = -1.0 * self.P * (dt / self.tau_p)
#        self.P += delta_P
#        
#        delta_c = -1.0 * self.c * (dt / self.tau_c)
#        self.c += delta_c
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
#    def reward(self):
#        # apply tag
#        self.efficiency += self.c
#        
#        # clamp to allowed range
#        if self.efficiency > self.max_efficiency:
#            self.efficiency = self.max_efficiency
#        elif self.efficiency < self.min_efficiency:
#            self.efficiency = self.min_efficiency
#                
## using "integrate-and-reward" discrete model
#class DopamineManager:
#    def __init__(self, equilibrium, tau, threshold):
#        self.equilibrium = equilibrium
#        self.level = equilibrium
#        self.tau = tau
#        self.threshold = threshold
#        
#        self.reward_listeners = []
#        self.reward_pending = False
#
#    def add_dopamine(self, ammount):
#        self.level += ammount
#        
#    def step(self, dt):
#        if self.level >= self.threshold:
#            self.reward_pending = True
#            self.level = self.equilibrium
#        else: # decay exponentially
#            delta = (self.equilibrium - self.level) * (dt / self.tau)
#            self.level += delta
#            
#    def exchange(self):
#        if self.reward_pending == True:
#            self.notify_reward_listeners()
#            self.reward_pending = False
#
#    def get_sample(self):
#        return self.level
#        
#    def add_reward_listener(self, listener):
#        self.reward_listeners.append(listener)
#        
#    def notify_reward_listeners(self):
#        for listener in self.reward_listeners:
#            listener.reward()
