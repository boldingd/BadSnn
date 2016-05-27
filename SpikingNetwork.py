# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 20:08:47 2016

@author: boldingd
"""

import SnnBase
import random


class Cluster:
    def __init__(self):
        self.neurons = []
        
    def add_neuron(self, neuron):
        self.neurons.append(neuron)
            
def create_pulsar_cluster(count, total_power, freq_min, freq_max):
    if count < 1:
        raise ValueError("Pulsar count must be positive")
        
    freqs = SnnBase.linspace(freq_min, freq_max, count) # will throw if freqs are wrong
    
    c = Cluster()
    
    per_pulsar_power = total_power / count
    
    for freq in freqs:
        per_pulse_power = per_pulsar_power / freq # # forgot to split power up over pulses
        p = SnnBase.Pulsar(per_pulse_power, freq)
        c.add_neuron(p)
        
    return c
    
def create_spiking_cluster(count, threshold, magnitude, leak_eql, leak_tau):
    c = Cluster()    
    
    for _ in range(count):
        sn = SnnBase.SpikingNeuron(threshold, magnitude, leak_eql, leak_tau)
        c.add_neuron(sn)
        
    return c
    
def create_poisson_cluster(count, total_power, freq_min, freq_max):
    if count < 1:
        raise ValueError("Pulsar count must be positive")
        
    freqs = SnnBase.linspace(freq_min, freq_max, count)
    
    c = Cluster()
    
    per_spiker_power = total_power / count # divide total power of spikers
    
    for freq in freqs:
        per_spike_power = per_spiker_power / freq # divide spiker power over pulses
        p = SnnBase.PoissonSpiker(per_spike_power, freq)
        c.add_neuron(p)
        
    return c

class BasicSynapseConnector:
    def __init__(self, delay, minimum_weight, maximum_weight):
        self.delay = delay
        self.minimum_weight = minimum_weight
        self.maximum_weight = maximum_weight
    
    def connect(self, source, target):
        e = random.uniform(self.minimum_weight, self.maximum_weight)
            
        syn = SnnBase.Synapse.Connect(source, target, self.delay, e, self.min_efficiency, self.max_efficiency)
        
        return syn

class StdpSynapseConnector:
    def __init__(self, delay, min_efficiency, max_efficiency):
        self.delay = delay
        self.min_efficiency = min_efficiency
        self.max_efficiency = max_efficiency
    
    def connect(self, source, target):
        e = random.uniform(self.min_efficiency, self.max_efficiency)
        
        syn = SnnBase.StdpSynapse.Connect(source, target, self.delay, e, self.min_efficiency, self.max_efficiency)
        
        return syn
            
# NOTE: Network manages connection, but not state.  For now, just yield your entities and let something else run the sim
class Network:
    def __init__(self):
        self.clusters = []
        self.synapses = []
        
    def get_new_cluster(self):
        """add a new cluster and return it.
        it's assumed the user will populate it externally.
        """
        c = Cluster()
        self.clusters.append(c)
        return c
        
    def add_cluster(self, cluster):
        if cluster in self.clusters:
            raise ValueError("Network already contains cluster")
            
        self.clusters.append(cluster)
        
    def connect_clusters(self, source_cluster, target_cluster, connector):
        if source_cluster not in self.clusters:
            raise ValueError("source cluster must be in this network")
            
        if target_cluster not in self.clusters:
            raise ValueError("target cluster must be in this network")
            
        if len(source_cluster.neurons) < 1:
            raise ValueError("Source cluster is empty")
            
        if len(target_cluster.neurons) < 1:
            raise ValueError("Target cluster is empty")
            
        for source in source_cluster.neurons:
            for target in target_cluster.neurons:
                syn = connector.connect(source, target)
                self.synapses.append(syn)
                
    def get_entities(self):
        entities = []
        
        for cluster in self.clusters:
            entities += cluster.neurons
            
        entities += self.synapses
        
        return entities
                            
# TODO: could track synapses more closely
# TODO: could keep track of which clusters have had synapses attached and prevent operations that don't make sense