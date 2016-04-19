# -*- coding: utf-8 -*-
"""
Created on Tue Mar 29 17:26:09 2016

@author: boldingd
"""

import SnnBase
import SpikingNetwork
import DopamineStdp

import random


# structure:
# pulsars (freq ranges)
#   fully connected, dop-mod synapses
# excitatory neurons (~10?)
#   fully connected, dop-mod synapses
# excitatory neurons (~10?)
#   fully connected, dop-mod synapses
# output layer (two excitatory neurons)
#   non-plastic synapses
# pattern detector
#   dopamine system

class DopamineSynapseConnector:
    def __init__(self, delay, min_efficiency, max_efficiency, reward_manager):
        self.delay = delay
        self.min_efficiency = min_efficiency
        self.max_efficiency = max_efficiency
        
        self.reward_manager = reward_manager
    
    def connect(self, source, target):
        weight = random.uniform(self.min_efficiency, self.max_efficiency)
        
        syn = DopamineStdp.DopamineStdpSynapse(self.delay, weight, self.min_efficiency, self.max_efficiency) # delay / efficiency / min / max
        syn.add_target(target)
        source.add_synapse(syn)
        target.add_spike_listener(syn)
        
        self.reward_manager.add_rewardable(syn)      
        
        return syn

# FIXME: zero delay introduces order ambiguity
class CallbackSynapse:
    def __init__(self, callback, args = None):
        self.callback = callback
        self.received_spike = False
        self.args = args
        
    def add_spike(self, magnitude):
        self.received_spike = True
        
    def step(self, delta):
        if self.received_spike:
            if self.args is not None:
                self.callback(self.args)
            else:
                self.callback()
                
            self.received_spike = False

class Trainer:
    _start = 1
    _delaying = 2
    _b_listening = 3
    
    def __init__(self, reward_manager, neur_a, neur_b, delay, window):
        self.reward_manager = reward_manager
        
        self._state = Trainer._start
        
        # hold ca and cb to step them?
        self.ca = CallbackSynapse(lambda: self._notify_a()) # these should be ~closures?
        neur_a.add_synapse(self.ca)
        
        self.cb = CallbackSynapse(lambda: self._notify_b())
        neur_b.add_synapse(self.cb)
        
        self.delay = delay
        self.remaining_delay = 0.0
        self.window = window
        self.remaining_window = 0.0
        
        self.delay_expired = False
        self.window_expired = False
        
        self.a_received = False
        self.b_received = False
        
        self.reward = False
        
        # character listeners, dumb system to separate recording from actual reward management
        self.listeners = list()
        
    def _notify_a(self):
        self.a_received = True
            
        self._notify("a")
            
    def _notify_b(self):
        self.b_received = True
            
        self._notify("b")
        
    def prepare(self):
        # put the state transition in here
        if self._state == Trainer._start:
            if self.a_received and not self.b_received:
                self._state = Trainer._delaying
                self.remaining_delay = self.delay
                self.remaining_window = 0.0 # clear any window-timer that's running
        elif self.state == Trainer._delaying:
            if self.a_received or self.b_received:
                self._state = Trainer._delaying
                # clear any running timers
                self.remaining_delay = 0.0
                self.remaining_window = 0.0
            elif self.delay_expired:
                self._state = Trainer._b_listening
                self.remaining_delay = 0.0 # we already know this if delay_expired is true, but being consistent
                self.remaining_window = self.window
        elif self.state == Trainer._b_listening:
            if self.a_received: # reset
                self._state = Trainer._start
                self.remaining_delay = 0.0
                self.remaining_window = 0.0
            elif self.b_received: # reward and reset
                self.reward = True
                self._state = Trainer._start
                self.remaining_delay = 0.0
                self.remaining_window = 0.0
            elif self.window_expired: # reset, but only if we didn't also get b
                self._state = Trainer._start
                self.remaining_delay = 0.0
                self.remaining_window = 0.0
        
        # clear flags
        self.delay_expired = False
        self.window_expired = False
        self.a_received = False
        self.b_received = False
        
    def step(self, dt):
        self.ca.step(dt)
        self.cb.step(dt)
        
        if self.remaining_window > 0.0:
            self.remaining_window -= dt
            
            if self.remaining_window <= 0.0:
                self.window_expired = True
                self.remaining_window = 0.0
                
        if self.remaining_delay > 0.0:
            self.remaining_delay -= dt
            
            if self.remaining_delay <= 0.0:
                self.delay_expired = True
                self.remaining_delay = 0.0
                
    def exchange(self):
        if self.reward:
            self.reward_manager.add_dopamine(0.02)
                
    def add_listener(self, listener):
        self.listeners.append(listener)
        
    def _notify(self, symbol):
        for listener in self.listeners:
            listener.notify(symbol)
            
class SymbolTracker:
    def __init__(self, name=None):
        self.symbols = list()
        
        self.state = []
        self.history = []
        
        self.time = 0.0
        
        self.name = name
        
    def notify(self, symbol):
        self.state.append(symbol)
        
    def prepare(self):
        if len(self.state) > 0:
            history_entry = [self.time]
            history_entry += self.state
            self.history.append(history_entry)
            self.state = []
        
    def step(self, dt):
        self.time += dt
    
    def exchange(self):
        pass
    
    def report(self, fname=None):
        out_path = fname
        if out_path is None:
                if self.name is not None:
                    out_path = self.name + ".dat"
                else:
                    raise SnnBase.SnnError("Could not pick unique file name")
                
        with open(out_path, "w") as ofile:
            for item in self.history:
                for symbol in item:
                    ofile.write(str(symbol) + " ")
                ofile.write("\n")

rm = DopamineStdp.RewardManager(equilibrium=0.01, tau=15.0)

n = SpikingNetwork.Network()
c1 = SpikingNetwork.create_pulsar_cluster(10, 20.0, 1.0, 10.0)
c2 = SpikingNetwork.create_spiking_cluster(8, 50.0, 20.0, 0.0, 1.0) # count / thres / mag / leak_eql / tau
n.add_cluster(c1)
n.add_cluster(c2)
con = DopamineSynapseConnector(0.001, 0.25, 1.75, rm)
n.connect_clusters(c1, c2, con)

out_a = SnnBase.SpikingNeuron(60.0, 20.0, 0.0, 0.5) # thresh / mag / eql / tau
out_b = SnnBase.SpikingNeuron(60.0, 20.0, 0.0, 0.5)

cout = n.get_new_cluster()
cout.add_neuron(out_a)
cout.add_neuron(out_b)
n.connect_clusters(c2, cout, con)

count_a = SnnBase.Counter(name="a spikes")
count_a_syn = SnnBase.Synapse(0.0001, 1.0)
out_a.add_synapse(count_a_syn)
count_a_syn.add_target(count_a)

count_b = SnnBase.Counter(name="b spikes")
count_b_syn = SnnBase.Synapse(0.0001, 1.0)
out_b.add_synapse(count_b_syn)
count_b_syn.add_target(count_b)

t = Trainer(rm, out_a, out_b, delay=1.0, window=1.0)
s = SymbolTracker(name="symbols")
t.add_listener(s)

class ProgressNotifier:
    def __init__(self, frequency=1.0, callback=None):
        self.gap = 1.0 / frequency
        self.remaining_gap = self.gap
        self.callback = callback
        
        self.notify = False
        
        self.time = 0.0
        
    def step(self, dt):
        self.time += dt
        
        self.remaining_gap -= dt
        
        if self.remaining_gap <= 0.0:
            self.remaining_gap = self.gap
            self.notify = True
            
    def exchange(self):
        if self.notify:
            self.notify = False
            
            if self.callback is None:
                print("notify: ", self.time)
            else:
                self.callback(self.time)

entities = n.get_entities()
entities += [rm, t, s, count_a, count_a_syn, count_b, count_b_syn]
entities.append(ProgressNotifier(5.0))
SnnBase.run_simulation(2000.0, 1.0 / 1500.0, entities)

count_a.report()
count_b.report()

s.report()

