# -*- coding: utf-8 -*-
"""
Created on Mon Apr 11 18:19:21 2016

@author: boldingd
"""

import SnnBase
import SpikingNetwork
import DopamineStdp


class SpikeRewarder:
    """ticks up the dopamine manager every time a spike is received"""
    
    def __init__(self, reward_manager, per_spike_multiplier):
        self.reward_manager = reward_manager
        
        self.waiting_spikes = list()
        self.outgoing_spikes = list()
        
        self.per_spike_multiplier = per_spike_multiplier
        
    def step(self, dt):
        self.outgoing_spikes = self.waiting_spikes
        self.waiting_spikes = list()
        
    def add_spike(self, mag):
        self.waiting_spikes.append(mag)
        
    def exchange(self):
        for spike in self.outgoing_spikes:
            incr = spike * self.per_spike_multiplier
            self.reward_manager.add_reward(incr)


#pulsar_5hz = SnnBase.get_pulsar_for_frequency(power=80.0, frequency=5.0)
pulsar_5hz = SnnBase.Pulsar(magnitude=80.0, frequency=5.0)

spiker = SnnBase.SpikingNeuron(threshold=50.0, magnitude=30.0, leak_eql=0.0, leak_tau=0.75)

counter = SnnBase.Counter(name="spikes")
spiker.add_spike_listener(counter)

dsyn_pulsar_spiker = DopamineStdp.DopamineStdpSynapse(delay=0.001, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7)
pulsar_5hz.add_synapse(dsyn_pulsar_spiker)
dsyn_pulsar_spiker.add_target(spiker)
spiker.add_spike_listener(dsyn_pulsar_spiker)

rmanager = DopamineStdp.RewardManager(equilibrium=0.1, tau=10.0)
rmanager.add_rewardable(dsyn_pulsar_spiker)

rewarder = SpikeRewarder(rmanager, 0.1)
syn_spiker_rewarder = SnnBase.Synapse(delay=0.0, efficiency=1.0) # 0-delay should ~work now
spiker.add_synapse(syn_spiker_rewarder)
syn_spiker_rewarder.add_target(rewarder)

syn_sampler = SnnBase.Sampler(source=dsyn_pulsar_spiker, interval= 1.0/50.0, name="synapse efficiency")

dop_sampler = SnnBase.Sampler(source=rmanager, interval=1.0/50.0, name="dopamine level")

entities = [pulsar_5hz, spiker, counter, dsyn_pulsar_spiker, rmanager, rewarder, syn_spiker_rewarder, syn_sampler, dop_sampler]
SnnBase.run_simulation(200.0, 1.0 / 2000.0, entities)

counter.report()

syn_sampler.report()

dop_sampler.report()
