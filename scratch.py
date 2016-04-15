# -*- coding: utf-8 -*-
"""
Created on Tue Apr  5 20:54:35 2016

@author: boldingd
"""

import SnnBase

pulsar = SnnBase.Pulsar(30.0, 3.0) # 15 mag, 3Hz

rando = SnnBase.NaiveRandomSpiker(15, 2.0) # 50 mag, 1Hz avg

n1 = SnnBase.SpikingNeuron(60.0, 50.0, 0.0, 2.0) # thresh / mag / eql / tau

cr = SnnBase.Counter("n1 counter")
n1.add_spike_listener(cr)

syn_pulsar_n1 = SnnBase.StdpSynapse(0.001, 1.0, 0.4, 1.6) # delay / efficiency / min / max
pulsar.add_synapse(syn_pulsar_n1)
syn_pulsar_n1.add_target(n1)
n1.add_spike_listener(syn_pulsar_n1)

sr = SnnBase.Sampler(syn_pulsar_n1, 1.0 / 40.0, "syn")

syn_rando_n1 = SnnBase.Synapse(0.001, 1.0) # delay / efficiency
rando.add_synapse(syn_rando_n1)
syn_rando_n1.add_target(n1)

entities = [ pulsar, rando, n1, cr, syn_pulsar_n1, syn_rando_n1, sr ]

print("running")

try:
    SnnBase.run_simulation(20.0, 1.0 / 2000.0, entities)
except Exception as e:
    print("Blammo:\n\t" + e)

cr.report()
sr.report()

print("done")