#! /usr/bin/python3

import SnnBase
import Stdp
import DopamineStdp

import random


class TogglePulsar:
    def __init__(self, magnitude, frequency):
        self.magnitude = magnitude
        self.frequency = frequency # not used after construction at present
        self.delay = 1.0 / frequency
        self.remaining = self.delay

        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False

        self._active = False

        self._become_active = False
        self._become_inactive = False
        
    def step(self, dt):
        if self._become_active == True and self._active == False:
            self._active = True
            self._spike = False

            self.remaining = self.delay
        elif self._become_inactive == True and self._active == True:
            self._active = False

        if self._active:
            self.remaining -= dt

            if self.remaining <= 0.0:
                self.remaining = self.delay
                self._spike = True
            
    def exchange(self):
        if self._spike:
            for s in self.synapses:
                s.add_spike(self.magnitude)
                
            for listener in self.spike_listeners:
                listener.notify_of_spike()
                
            self._spike = False
        
    def add_synapse(self, ps):
        self.synapses.append(ps)
        
    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)

    def queue_activation(self):
        self._become_active = True
        self._become_inactive = False

    def queue_inactivation(self):
        self._become_active = False
        self._become_inactive = True

    def get_is_active(self):
        return self._active


class RateTracker:
    def __init__(self, high_threshold, low_threshold, window):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

        self.window = window

        self.remaining_times = []

        self._high_state = False

        self.callbacks = []
        self.run_callbacks = False

    def step(self, dt):
        self.remaining_times = [ time - dt for time in self.remaining_times if time > dt ]

        if self._high_state:
            if len(self.remaining_times) <= self.low_threshold:
                self._high_state = False
                self.run_callbacks = True
        else:
            if len(self.remaining_times) >= self.high_threshold:
                self._high_state = True
                self.run_callbacks = True

    def exchange(self):
        if self.run_callbacks:
            self.run_callbacks = False
            for callback in self.callbacks:
                callback(self._high_state)

    def add_spike(self, magnitude):
        self.remaining_times.append(self.window)

    def add_change_callback(self, callback):
        self.callbacks.append(callback)

    def get_is_high(self):
        return self._high_state

    def get_freq(self):
        return len(self.remaining_times) / self.window


class CallbackManager:
    def __init__(self, freq):
        self.t = 0.0
        self.freq = freq
        self.wait = 1.0 / freq

        self.run_callbacks = False
        self.callbacks = []

    def step(self, dt):
        self.t += dt
        self.wait -= dt

        if self.wait <= 0.0:
            self.wait = 1.0 / self.freq
            self.run_callbacks = True

    def exchange(self):
        if self.run_callbacks:
            self.run_callbacks = False

            for callback in self.callbacks:
                callback(self.t) # note: if callback causes an AttributeError, that will get suppressed later

    def add_callback(self, callback):
        self.callbacks.append(callback)


class Manager:
    def __init__(self, tog_1, tog_2, rt, switch_wait, reward_wait):
        self.tog_1 = tog_1
        self.tog_2 = tog_2
        self.t1 = False
        self.t2 = False

        self.rt = rt

        self.switch_wait = switch_wait
        self._s_wait = 0.0

        self.reward_wait = reward_wait
        self._r_wait = 0.0

        self._toggle_change = True

        self.rewardables = []

    def add_rewardable(self, rable):
        self.rewardables.append(rable)

    def _set_rewards(self, r):
        for rable in self.rewardables:
            rable.reward(r)

    def step(self, dt):
        self._s_wait -= dt

        if self._s_wait <= 0:
            self._s_wait = self.switch_wait
            self._r_wait = self.reward_wait
            self._toggle_change = True

        self._r_wait -= dt # who cares if it's negative?

    def exchange(self):
        if self._toggle_change:
            self._toggle_change = False

            if random.random() < 0.5:
                self.t1 = False
                self.tog_1.queue_inactivation()
            else:
                self.t1 = True
                self.tog_1.queue_activation()

            if random.random() < 0.5:
                self.t2 = False
                self.tog_2.queue_inactivation()
            else:
                self.t2 = True
                self.tog_2.queue_activation()

        if self._r_wait <= 0.0:
            if self.t1 == True and self.t2 == True:
                if self.rt.get_is_high():
                    self._set_rewards(0.0)
                else:
                    self._set_rewards(0.001)
            else:
                if self.rt.get_is_high():
                    self._set_rewards(-0.001)
                else:
                    self._set_rewards(0.0)
        else:
            self._set_rewards(0.0)


tog_1 = TogglePulsar(magnitude=25.0, frequency=10.0)
tog_2 = TogglePulsar(magnitude=25.0, frequency=10.0)
ex = SnnBase.SpikingNeuron(threshold=50.0, magnitude=50.0, leak_eql=0.0, leak_tau=0.25)

rt = RateTracker(low_threshold=2, high_threshold=4, window=0.5)

syn_tog1_ex = DopamineStdp.DopamineStdpSynapse.connect(source=tog_1, target=ex, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=None)
syn_tog2_ex = DopamineStdp.DopamineStdpSynapse.connect(source=tog_2, target=ex, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=None)
syn_ex_rt   = SnnBase.Synapse.connect(source=ex, target=rt, delay=0.0, efficiency=1.0)

mg = Manager(tog_1, tog_2, rt, switch_wait=4.0, reward_wait=1.0)
mg.add_rewardable(syn_tog1_ex)
mg.add_rewardable(syn_tog2_ex)

cm = CallbackManager(freq=5.0)
cm.add_callback(lambda t: print("{:5f}: [{} {}]  =>  {:3g} {}".format(t, tog_1.get_is_active(), tog_2.get_is_active(), rt.get_freq(), rt.get_is_high())))
ofile = open("a synapse.dat", "w")
cm.add_callback(lambda t: ofile.write("{}:  {} {}\n".format(t, syn_tog2_ex.efficiency, syn_tog2_ex.c)))

entities = [tog_1, tog_2, ex, rt, syn_tog1_ex, syn_tog2_ex, syn_ex_rt, mg, cm]

SnnBase.run_simulation(1000.0, 1.0 / 1200.0, entities)

