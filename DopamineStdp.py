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
        self.r = 0.0 # store the reward signal
        
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
        
    def prepare(self):
        # apply r, modify efficiency and reset r
        # because reward signal might happen at any point during previous step's exchange
    
        # apply tag
        self.efficiency += self.r * self.c
        
        # clamp to allowed range
        if self.efficiency > self.max_efficiency:
            self.efficiency = self.max_efficiency
        elif self.efficiency < self.min_efficiency:
            self.efficiency = self.min_efficiency
            
        # reset reward accumulator
        self.r = 0.0
        # NB: this model "rests at 0", but not all models do.
        
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
                
    def reward(self, r):
        self.r += r # accumulate reward signals        

# assumption: add_reward will be called only during exchange step
class RewardManager:
    def __init__(self, equilibrium, tau):
        self.equilibrium = equilibrium
        self.tau = tau
        
        self.r = equilibrium
        
        self.rewardables = list()
        
        self.pending_rewards = list()
        
    def step(self, dt):
        dr = -1.0 * (self.r - self.equilibrium) * (dt / self.tau)
        
        for reward in self.pending_rewards:
            dr += reward
            
        self.r += dr
        
    def exchange(self):
        for rw in self.rewardables:
            rw.reward(self.r)
            
    def add_rewardable(self, rewardable):
        self.rewardables.append(rewardable)
        
    def add_reward(self, reward):
        self.pending_rewards.append(reward)
