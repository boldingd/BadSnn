#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 11 18:19:21 2016

@author: boldingd
"""

import SnnBase
import SpikingNetwork
import DopamineStdp

import sys

try:
    freq = int(sys.argv[1])
except Exception as e:
    print("Must provide target freq as first positional argument")
    sys.exit(1)

class SpikeRewarder:
    """ticks up the dopamine manager every time a spike is received"""
    
    def __init__(self, reward_manager, per_spike_multiplier):
        self.reward_manager = reward_manager
        
        self.waiting_spikes = list()
        self.outgoing_spikes = list()
        
        self.per_spike_multiplier = per_spike_multiplier
        
        self._reward = 0.0
        
    def step(self, dt):
        self.outgoing_spikes = self.waiting_spikes
        self.waiting_spikes = list()
        
        # compute reward val now so we can multiply it by dt
        self._reward = len(self.outgoing_spikes) * self.per_spike_multiplier * dt
        
    def add_spike(self, mag):
        self.waiting_spikes.append(mag)
        
    def exchange(self):
        self.reward_manager.add_reward(self._reward)
#        for spike in self.outgoing_spikes:
#            #incr = spike * self.per_spike_multiplier
#            self.reward_manager.add_reward( self.per_spike_multiplier )
            
class FrequencyAttractorRewarder:
    # state: spike arrival times
    # goal: make reward a function of deviation by observed frequency from target frequency
    # alg
    #     step: prune window
    #     exch: compute dr as function of deviation

    # window length is a parameter so that less-than-1hz frequencies can be used (in which case you'd want a window >> 1.0s)
    # amone other reasons
    def __init__(self, reward_manager, target_frequency, window_length=1.0, reward_increment=0.1):
        self.reward_manager = reward_manager
        self.target_frequency = target_frequency
        
        self.window_length = window_length
        
        self.reward_increment = reward_increment
        
        self._spike_waits = list()
        
        self.activation_delay = 2.0 * window_length
        
        self._reward = 0.0
        
    def step(self, dt):
        if self.activation_delay > 0.0:
            self.activation_delay -= dt
            
        waits = self._spike_waits
        self._spike_waits = [ wait - dt for wait in waits if wait >= dt ]
        
        # compute reward
        obs_freq = len(self._spike_waits) / self.window_length
        dev = (self.target_frequency - obs_freq) / self.target_frequency # normalize ~ size of target freq
        
        # scaled so dev is [0-1] when freq is [0, 2f]
        # freq    0.0      f        2f
        # dev     1.0      0.0      1.0
        
        self._reward = self.reward_increment * dt * dev
    
    def add_spike(self, mag):
        self._spike_waits.append(self.window_length)
    
    def exchange(self):
        if self.activation_delay > 0.0:
            return
        
        self.reward_manager.add_reward( self._reward )

#### manager and rewarder
rmanager = DopamineStdp.RewardManager(equilibrium=0.0, tau=3.0)

# set target frequency from command line arg above
rewarder = FrequencyAttractorRewarder(rmanager, target_frequency=freq, window_length=3.0, reward_increment=0.05)

#### build the network
pcluster = SpikingNetwork.create_pulsar_cluster(count=10, total_power=500.0, freq_min=1.0, freq_max=20.0)

spiker = SnnBase.SpikingNeuron(threshold=50.0, magnitude=30.0, leak_eql=0.0, leak_tau=0.5)
scluster = SpikingNetwork.Cluster()
scluster.add_neuron(spiker)

network = SpikingNetwork.Network()
network.add_cluster(pcluster)
network.add_cluster(scluster)

dcon = SpikingNetwork.DopamineStdpSynapseConnector(delay=0.0, min_efficiency=0.1, max_efficiency=1.9, reward_manager=rmanager)
network.connect_clusters(source_cluster=pcluster, target_cluster=scluster, connector=dcon)

#### connect the output spiker to the rewarder
outsyn = SnnBase.Synapse.connect(source = spiker, target = rewarder, delay = 0.0, efficiency = 1.0)

#### build entities and run sim
entities = network.get_entities()

#### set up callbacks
sample_dsyn = None
for en in entities:
    if issubclass(type(en), DopamineStdp.DopamineStdpSynapse):
        sample_dsyn = en
        break
if sample_dsyn is None:
    raise Exception("No synapses found")
    
def print_samples(t):
    freq = len(rewarder._spike_waits) / rewarder.window_length
    print("{} {}".format(t, freq))

cbm = SnnBase.CallbackManager(2)
cbm.add_callback(print_samples)   
    
entities += [rmanager, rewarder, outsyn, cbm]
SnnBase.run_simulation(200.0, 1.0 / 2000.0, entities)

print(str("done"))

