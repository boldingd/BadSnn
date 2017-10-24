"""
A module containing an Izhikevich spiking neuron
Theoretically, it has far more realistic sub-threshold beavior, while not being much more complex than an LIF neuron.
"More realistic sub-threshold dynamics" includes the ability to act as a resonator, which might be Handy.

See also:  https://www.izhikevich.org/publications/spikes.htm
"""

import SnnBase # for SnnError if nothing else

class IzhikevichNeuron:
    def __init__(self, a=0.02, b=0.2, c=-65.0, d=2.0, threshold=30.0):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.threshold = threshold

        self.v = self.c
        self.u = 0.0

        self.currents = list()

        self.spike_listeners = list()

        self.synapses = list()

        self.received_spikes = list()

        self.spike = False

    def step(self, dt):
        dv = (0.04 * (self.v ** 2)) + (5.0 * self.v) + 140.0 + - self.u

        # DC current model
        for current in self.currents:
            dv += current.I

        dv *= dt

        for spike in self.received_spikes:
            dv += spike

        self.received_spikes.clear()

        du = self.a * (self.b * self.v - self.u)

        self.v += dv
        self.u += du

        if self.v >= self.threshold:
            self.v = self.c
            self.u += self.d

            self.spike = True

    def exchange(self):
        if self.spike:
            for syn in self.synapses:
                syn.add_spike(self.threshold) # TODO: could change to use separate spike mag...

            for listener in self.spike_listeners:
                listener.notify_of_spike()

            self.spike = False

    def add_synapse(self, synapse):
        self.synapses.append(synapse)

    def add_spike_listener(self, listener):
        self.spike_listeners.append(listener)

    def add_current(self, current):
        self.currents.append(current)

    def add_spike(self, magnitude):
        self.received_spikes.append(magnitude)

