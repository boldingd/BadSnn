# -*- coding: utf-8 -*-
"""
Created on Wed Mar  1 03:59:39 2017

@author: boldingd
"""

import SnnBase
import DopamineStdp
import Utilities

import enum
import random

# current theory: the tau of 15 for the c constant means taht the learning window is 15 seconds wide, give or take.
# the problem might be that that's simply too long a history for these quick, back-to-back intervals.
# so, possibly, what we need to do is test it in pulses.
#    turn on inputs
#    two seconds of warm-up,
#    two seconds of observation,
#    turn off inputs
#    fifteen seconds of wind-down
# I might also try the [0,1] model of dopamine levels

class Controller:
    class State(enum.Enum):
        PULSE = 1
        COOLDOWN = 2
    
    def __init__(self, a_rate_tracker, b_rate_tracker):
        self._a_tracker = a_rate_tracker
        self._b_tracker = b_rate_tracker        
        
        self._a_togglables = list()
        self._b_togglables = list()
        
        self._a_active = False
        self._b_active = False
        
        self.pulse_window = 6.0
        self.cooldown_window = 20.0
        
        self._wait = self.cooldown_window
        self._state = Controller.State.COOLDOWN

        self.base_r = 0.1
        self._r = self.base_r
        self._r_tau = 1.0
        
        self._rewardables = list()
    
    def add_a_togglable(self, tog):
        self._a_togglables.append(tog)
        
    def add_b_togglable(self, tog):
        self._b_togglables.append(tog)
        
    def add_rewardable(self, rwable):
        self._rewardables.append(rwable)
        
    def step(self, dt):
        self._r += (self.base_r - self._r) * (dt / self._r_tau) # r exponentially decayse to base
        
        self._wait -= dt
        
        if self._wait <= 0.0:
            if  self._state == Controller.State.PULSE:
                # PULSE -> Cooldown
                self._state = Controller.State.COOLDOWN
                self._wait = self.cooldown_window
                
                # determine performance and set r (to 0.0 or 4*base)
                num_right = 0
                if self._a_tracker.get_is_high() == self._a_active:
                    num_right += 1
                if self._b_tracker.get_is_high() == self._b_active:
                    num_right += 1
                
                if num_right == 2:
                    self._r = 4.0 * self.base_r
                elif num_right == 1:
                    self._r = self.base_r
                else:
                    self._r = 0.0
                    
                print("({} {})  -->  ({} {})".format(self._a_active, self._b_active, self._a_tracker.high, self._b_tracker.high))
                    
                # NOTE: this is the part that's not quite right.
                # Well, a part.
                # Because I should really be tracking it's change-in-abs-error
                
                # deactivate pulsars and clean up state
                for t in self._a_togglables:
                    t.queue_inactivation()
                for t in self._b_togglables:
                    t.queue_inactivation()
                    
                self._a_active = False
                self._b_active = False
                
            else:
                # COOLDOWN -> PULSE
                self._state = Controller.State.PULSE
                self._wait = self.pulse_window
                
                # set R to zero (no dopamine effects during pulsing)
                self._r = 0.0 # revisit
                
                # pick pulsars to activate
                if random.random() >= 0.5:
                    # activate A group
                    for t in self._a_togglables:
                        t.queue_activation()                    
                    
                    self._a_active = True
                
                if random.random() >= 0.5:
                    # activate B group
                    for t in self._b_togglables:
                        t.queue_activation()                    
                    
                    self._b_active = True
                    
    def exchange(self):
        # set R
        for rwable in self._rewardables:
            rwable.reward(self._r)
            
        # don't worry about state: step will 0-out r when it needs to


entities = list()            

vpulse_a_1 = Utilities.VariableStochasticPulsar(magnitude=20.0, low_frequency = 1, high_frequency = 5)
vpulse_a_2 = Utilities.VariableStochasticPulsar(magnitude=20.0, low_frequency = 1, high_frequency = 5)

vpulse_b_1 = Utilities.VariableStochasticPulsar(magnitude=20.0, low_frequency = 1, high_frequency = 5)
vpulse_b_2 = Utilities.VariableStochasticPulsar(magnitude=20.0, low_frequency = 1, high_frequency = 5)

output_a = SnnBase.SpikingNeuron(threshold=60.0, magnitude=30.0, leak_eql=0.0, leak_tau=1.0)

output_b = SnnBase.SpikingNeuron(threshold=60.0, magnitude=30.0, leak_eql=0.0, leak_tau=1.0)

a_tracker = Utilities.ThresholdTracker(high_threshold=6, low_threshold=2, window=2.0)

b_tracker = Utilities.ThresholdTracker(high_threshold=6, low_threshold=2, window=2.0)

con = Controller(a_tracker, b_tracker)

# variables --> outputs
for v in [vpulse_a_1, vpulse_a_2, vpulse_b_1, vpulse_b_2]:
    for o in [output_a, output_b]:
        syn = DopamineStdp.DopamineStdpSynapse.connect(source=v, target=o, delay=0.0, efficiency=0.7, min_efficiency=0.3, max_efficiency=1.7, reward_manager=con)
        entities.append(syn)

# outputs --> trackers
output_a.add_spike_listener(a_tracker)
output_b.add_spike_listener(b_tracker)

# trackers --> con was done in the constructor for con
# con --> dopamine synapses is done in their constructor

# con --> variables (control)
con.add_a_togglable(vpulse_a_1)
con.add_a_togglable(vpulse_a_2)
con.add_b_togglable(vpulse_b_1)
con.add_b_togglable(vpulse_b_2)

entities += [vpulse_a_1, vpulse_a_2, vpulse_b_1, vpulse_b_2, output_a, output_b, a_tracker, b_tracker, con]

SnnBase.run_simulation(stop_time=500.0, step= 1.0 / 1000.0, entities=entities)
