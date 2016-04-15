# -*- coding: utf-8 -*-
"""
Created on Mon Apr 11 17:53:16 2016

@author: boldingd
"""

import SnnBase
import SpikingNetwork


network = SpikingNetwork.Network()
pulsar_cluster = SpikingNetwork.create_pulsar_cluster(20, 100, 2.0, 20.0) # count / total power / min-freq / max-freq
network.add_cluster(pulsar_cluster)
out_cluster = network.get_new_cluster()

spiker = SnnBase.SpikingNeuron(threshold=30.0, magnitude=60.0, leak_eql=0.0, leak_tau=0.5)
out_cluster.add_neuron(spiker)
spike_counter = SnnBase.Counter("uncle john's counter")
spiker.add_spike_listener(spike_counter)

stdp_connector = SpikingNetwork.StdpSynapseConnector(0.001, 0.4, 1.6) # delay / min / max
network.connect_clusters(pulsar_cluster, out_cluster, stdp_connector)

entities = network.get_entities()
entities.append(spike_counter)

SnnBase.run_simulation(200.0, 1.0 / 2000.0, entities)

spike_counter.report()
