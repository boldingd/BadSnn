# -*- coding: utf-8 -*-
"""
Created on Tue May 24 17:59:24 2016

@author: boldingd
"""


import SnnBase


class GapCounter:
    def __init__(self, name):
        self.name = name
        self.time = 0.0
        
        self.gaps = []
        
        self.last_spike = 0.0
    
    def step(self, dt):
        self.time += dt
    
    def notify_of_spike(self):
        self.gaps.append(self.time - self.last_spike)
        self.last_spike = self.time
    
    def report(self):
        fname = self.name + ".dat"
        with open(fname, "w") as ofile:
            for gap in self.gaps:
                ofile.write(str(gap) + "\n")


# each is 10 Hz
poisson = SnnBase.PoissonSpiker(1.0, 10.0)
naive = SnnBase.NaiveRandomSpiker(1.0, 10.0)
pulsar = SnnBase.Pulsar(1.0, 10.0)

poisson_counter = SnnBase.Counter(name="poisson")
poisson.add_spike_listener(poisson_counter)

naive_counter = SnnBase.Counter(name="naive")
naive.add_spike_listener(naive_counter)

pulsar_counter = SnnBase.Counter(name="pulsar")
pulsar.add_spike_listener(pulsar_counter)

poisson_gaps = GapCounter(name="poisson_gaps")
poisson.add_spike_listener(poisson_gaps)

entities = [poisson, naive, pulsar, poisson_counter, naive_counter, pulsar_counter, poisson_gaps]
SnnBase.run_simulation(10.0, 1.0 / 1000.0, entities)


poisson_counter.report()
naive_counter.report()
pulsar_counter.report()
poisson_gaps.report()