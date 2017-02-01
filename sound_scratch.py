#! /usr/bin/python3

import SnnBase
import Stdp
import DopamineStdp

import random


class StochasticNeuron:
    def __init__(self, saturation_level, saturation_rate, magnitude, leak_eql, leak_tau):
        self.s_level = saturation_level
        self.s_rate = saturation_rate

        selt.magnitude = magnitude
        self.leak_eql = leak_eql
        self.leak_tau = leak_tau

        self._charge = leak_eql

        self.synapses = []

        self.spike_listeners = []

        self._spike = False

    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)

    def add_synapse(self, synapse):
        self.synapses.append(synapses)

    def step(self, dt):
        self._charge += (self.leak_eql - self._charge) * (dt / self._leak_tau)

        prob = (self.s_rate / dt)
        if self._charge < self.s_level:
            prob *= self._charge / self.s_level

        if random.random() <= prob:
            self._charge = self.leak_eql
            self._spike = True

    def exchange(self):
        if self._spike == True:
            self._spike = False

            for syn in self.synapses:
                syn.add_spike(self.magnitude)

            for lsnr in self.spike_listeners:
                lsnr.notify_of_spike()


class DrivenStochasticNeuron(StochasticNeuron):
    def __init__(self, driving_function, saturation_level, saturation_rate, magnitude, leak_eql, leak_tau):
        super().__init__(saturation_level, saturation_rate, magnitude, leak_eql, leak_tau)

        self.func = driving_function
        self._t = 0.0

    def step(self, dt):
        # complex ion-channel-like model?  Or simple dt * func?

        self._t += dt
        self.channel += dt * self.func(self._t)

        super().step(dt)

def func(t):
    pass



# quick test

class TestAccm:
    def __init__(self, freq, func):
        self.freq = freq
        self._m = 1.0 / freq
        self._tau = freq

        self._accm = 0.0

        self.f = func

        self._t = 0.0

    def step(self, dt):
        self._accm += self.f(self._t)

        self._accm += -accm * (dt / self._tau)

        self._t += dt

