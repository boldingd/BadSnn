#! /usr/bin/python3

import SnnBase
import SpikingNetwork
import DopamineStdp

import math
import sys
import random

#window needs to be at least 2/freq, and preferable more than that
#however, a long window will also lead to very delayed responses when frequencies shift
class FrequencyRewarder:
    def __init__(self, target_freq, window, reward_wait=None, base_r=0.2):
        self.target_freq = target_freq
        self._spike_waits = list()
        self.window = window

        if reward_wait is None:
            self.reward_wait = window
        else:
            self.reward_wait = reward_wait
        self._r_wait = self.reward_wait
        
        self._last_freq = None

        self._base_r = base_r
        self._r = base_r

        self._rewardables = list()

    def add_rewardable(self, rewardable):
        self._rewardables.append(rewardable)

    def _set_rewards(self, r):
        for rwable in self._rewardables:
            rwable.reward(r)

    def step(self, dt):
        self._spike_waits = [ wait - dt for wait in self._spike_waits if wait >= dt ]

        self._r_wait -= dt
        if self._r_wait <= 0.0:
            self._r_wait = self.reward_wait

            freq = len(self._spike_waits) / self.window

            if self._last_freq is not None:
                e_prev = self.target_freq - self._last_freq
                e_cur  = self.target_freq - freq

                de = e_cur - e_prev

                if de <= -1.0: # if we made a large improvement
                    self._r = 2.0 * self._base_r
                elif de >= 1.0: # if we actually got worse
                    self._r = 0.0
                else: # if our error is ~~stable
                    self._r = self._base_r

            self._last_freq = freq

    def exchange(self):
        self._set_rewards(self._r)

    def add_spike(self, mag):
        self._spike_waits.append(self.window)
        
    # being lazy, skiping the non-plastic synapse
    def notify_of_spike(self):
        self._spike_waits.append(self.window)


class StochasticPulsar:
    def __init__(self, magnitude, frequency):
        self.magnitude = magnitude
        self.frequency = frequency

        self.synapses = list()

        self.spike_listeners = list()

        self._spike = False

    def step(self, dt):
        if random.random() <= self.frequency * dt:
            self._spike = True

    def exchange(self):
        if self._spike:
            for s in self.synapses:
                s.add_spike(self.magnitude)

            for listener in self.spike_listeners:
                listener.notify_of_spike()

            self._spike = False

    def add_synapse(self, syn):
        self.synapses.append(syn)

    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)


class SinfulNotifier:
    def __init__(self):
        self.t = 0.0
        
        self.spike_count = 0        
        
    def step(self, dt):
        self.t += dt
        
    def notify_of_spike(self):
        print("{}: got notification".format(self.t))
        self.spike_count += 1


entities = list()


# build the network
output = SnnBase.SpikingNeuron(50.0, 30.0, 0.0, 1.0)

rewarder = FrequencyRewarder(target_freq=5.0, window=2.0)
output.add_spike_listener(rewarder)

entities.append(output)
entities.append(rewarder)


# build stochastic pulsars
power = 100.0

freq_min = 1.0
freq_max = 20.0
freq_count = 5.0
per_freq = 2 # must be into to be an argument to range

count = freq_count * per_freq
per_unit_power = power / count

f = freq_min
while f <= freq_max:
    for i in range(per_freq):
        per_spike_power = per_unit_power / f
        sp = StochasticPulsar(per_spike_power, f)
    
        entities.append(sp)
        
        syn = DopamineStdp.DopamineStdpSynapse.connect(source=sp, target=output, delay=0.0, efficiency=0.7, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rewarder)
        entities.append(syn)
    
    f += (freq_max - freq_min) / (freq_count - 1)


#sin = SinfulNotifier()
#entities[9].add_spike_listener(sin)
#entities.append(sin)


cb = SnnBase.CallbackManager(freq=20.0)
cb.add_callback(lambda t: print("{}: {}r {}hz".format(t, rewarder._r, rewarder._last_freq)))
entities.append(cb)

SnnBase.run_simulation(100.0, 1.0 / 1000.0, entities)