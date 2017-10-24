#! /usr/bin/python3

import SnnBase
import Stdp
import DopamineStdp

import random


class NoisySpikingNeuron(SnnBase.SpikingNeuron):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.gross_error = 0.0

        self._spike_mode = random.choice([True, False])

    def set_gross_error(self, gross_error):
        self.gross_error = gross_error

    def step(self, dt):
        super().step(dt)

        # changing membrane voltage only makes sense if we didn't decide to spike this tic
        if self.spike == False:
            if random.random() <= self.gross_error * 4 * dt: # for now, fixed 25%-per-second chance of spike
                if self._spike_mode:
                    self.charge = self.eql
                    self.spike = True
                else:
                    self.charge -= self.gross_error * self.eql * (dt / 0.1) # decay swiftly to eql


class NoisyDopamineSynapse(DopamineStdp.DopamineStdpSynapse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.total_abs_error = 0.0

        self.wait = 1.0
        self._wait = 0.0

        self.err_eql = 0.0

    # assume error is normalized to [0,1]
    def set_total_abs_error(self, error):
        self.total_abs_error = error

    def step(self, dt):
        super().step(dt)

        if self._wait > 0.0:
            self._wait -= dt
        else:
            self._wait = self.wait
            self.err_eql = random.choice([self.max_efficiency, self.min_efficiency])

        self.efficiency += self.total_abs_error * (dt / (2 * self.wait)) * (self.efficiency - self.err_eql)

    @staticmethod
    def connect(source, target, delay, efficiency, min_efficiency, max_efficiency, reward_manager=None):
        s = NoisyDopamineSynapse(delay, efficiency, min_efficiency, max_efficiency)
        
        s.add_target(target)
        source.add_synapse(s)
        
        target.add_spike_listener(s)
        
        if reward_manager is not None:
            reward_manager.add_rewardable(s)
        
        return s


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


class ToggleRandomPulsar:
    def __init__(self, magnitude, frequency):
        self.magnitude = magnitude
        self.frequency = frequency # not used after construction at present
        self.prob = 1.0 / frequency

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
        elif self._become_inactive == True and self._active == True:
            self._active = False

        if self._active:
            if random.random() < self.prob * dt:
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


class VariableStochasticPulsar:
    def __init__(self, magnitude, low_frequency, high_frequency):
        self.magnitude = magnitude
        self.high_frequency = high_frequency # not used after construction at present
        self.low_frequency = low_frequency
        #self._prob = 1.0 / low_frequency
        self._prob = low_frequency

        self.synapses = []
        
        self.spike_listeners = []
        
        self._spike = False

    def step(self, dt):
        if random.random() < self._prob * dt:
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
        self._prob = self.high_frequency

    def queue_inactivation(self):
        self._prob = self.low_frequency


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
    def __init__(self, rt_1, rt_2, switch_wait, reward_wait):
        self.togs_1 = []
        self.togs_2 = []
        self.t1 = False
        self.t2 = False

        self.rt_1 = rt_1
        self.rt_2 = rt_2

        self.switch_wait = switch_wait
        self._s_wait = 0.0

        self.reward_wait = reward_wait
        self._r_wait = 0.0

        self._toggle_change = True

        self.rewardables = []

        self.gross_error_trackers = []

    def add_rewardable(self, rable):
        self.rewardables.append(rable)

    def add_gross_error_tracker(self, tracker):
        self.gross_error_trackers.append(tracker)

    def add_1_togglable(self, togglable):
        self.togs_1.append(togglable)

    def add_2_togglable(self, togglable):
        self.togs_2.append(togglable)

    def _set_rewards(self, r):
        for rable in self.rewardables:
            rable.reward(r)

    def _set_gross_error(self, e):
        for tracker in self.gross_error_trackers:
            tracker.set_gross_error(e)

    def step(self, dt):
        self._s_wait -= dt

        self._r_wait -= dt # who cares if it's negative?

        if self._s_wait <= 0:
            self._s_wait = self.switch_wait
            self._r_wait = self.reward_wait
            self._toggle_change = True

    def exchange(self):
        if self._toggle_change:
            self._toggle_change = False

            if random.random() < 0.5:
                self.t1 = False
                for tog in self.togs_1:
                    tog.queue_inactivation()
            else:
                self.t1 = True
                for tog in self.togs_1:
                    tog.queue_activation()

            if random.random() < 0.5:
                self.t2 = False
                for tog in self.togs_2:
                    tog.queue_inactivation()
            else:
                self.t2 = True
                for tog in self.togs_2:
                    tog.queue_activation()

        if self._r_wait <= 0.0:
            # set dopamine level
            r = 0.0

            if self.t1 == True:
                if not self.rt_1.get_is_high():
                    r += 0.01
            else: # selt.t1 is low
                if self.rt_1.get_is_high():
                    r -= 0.01

            if self.t2 == True:
                if not self.rt_2.get_is_high():
                    r += 0.01
            else: # self.t2 is low
                if self.rt_1.get_is_high():
                    r -= 0.01

            self._set_rewards(r)

            # set gross-error
            e = 0.0

            if self.t1 != self.rt_1.get_is_high():
                e += 0.5

            if self.t2 != self.rt_2.get_is_high():
                e += 0.5

            self._set_gross_error(e)


class AlternatingPhaseManager:
    def __init__(self, rt_1, rt_2, switch_wait, reward_wait, test_wait):
        self.togs_1 = []
        self.togs_2 = []
        self.t1 = False
        self.t2 = False

        self.rt_1 = rt_1
        self.rt_2 = rt_2

        self.switch_wait = switch_wait
        self._s_wait = 0.0

        self.reward_wait = reward_wait
        self._r_wait = 0.0

        self.test_wait = test_wait
        self._t_wait = test_wait

        self._toggle_change = True

        self.rewardables = []

        self.gross_error_trackers = []

    def add_rewardable(self, rable):
        self.rewardables.append(rable)

    def add_gross_error_tracker(self, tracker):
        self.gross_error_trackers.append(tracker)

    def add_1_togglable(self, togglable):
        self.togs_1.append(togglable)

    def add_2_togglable(self, togglable):
        self.togs_2.append(togglable)

    def _set_rewards(self, r):
        for rable in self.rewardables:
            rable.reward(r)

    def _set_gross_error(self, e):
        for tracker in self.gross_error_trackers:
            tracker.set_gross_error(e)

    def step(self, dt):
        self._s_wait -= dt

        if self._s_wait <= 0:
            self._s_wait = self.switch_wait
            self._r_wait = self.reward_wait
            self._toggle_change = True

        self._r_wait -= dt # who cares if it's negative?

        self._t_wait -= dt

    def _train_exchange(self):
        #TODO: thinking about trying to get this to work

        if self._toggle_change:
            self._toggle_change = False

            if random.random() < 0.5:
                self.t1 = False
                for tog in self.togs_1:
                    tog.queue_inactivation()
            else:
                self.t1 = True
                for tog in self.togs_1:
                    tog.queue_activation()

            if random.random() < 0.5:
                self.t2 = False
                for tog in self.togs_2:
                    tog.queue_inactivation()
            else:
                self.t2 = True
                for tog in self.togs_2:
                    tog.queue_activation()

        if self._r_wait <= 0.0:
            r = 0.0

            if self.t1 == True:
                if not self.rt_1.get_is_high():
                    r += 0.01
            else: # selt.t1 is low
                if self.rt_1.get_is_high():
                    r -= 0.01

            if self.t2 == True:
                if not self.rt_2.get_is_high():
                    r += 0.01
            else: # self.t2 is low
                if self.rt_1.get_is_high():
                    r -= 0.01

            self._set_rewards(r)

            # set gross-error
            e = 0.0

            if self.t1 != self.rt_1.get_is_high():
                e += 0.5

            if self.t2 != self.rt_2.get_is_high():
                e += 0.5

            self._set_gross_error(e)

    def _tune_exchange(self):
        if self._toggle_change:
            self._toggle_change = False

            if random.random() < 0.5:
                self.t1 = False
                for tog in self.togs_1:
                    tog.queue_inactivation()
            else:
                self.t1 = True
                for tog in self.togs_1:
                    tog.queue_activation()

            if random.random() < 0.5:
                self.t2 = False
                for tog in self.togs_2:
                    tog.queue_inactivation()
            else:
                self.t2 = True
                for tog in self.togs_2:
                    tog.queue_activation()

        if self._r_wait <= 0.0:
            r = 0.0

            if self.t1 == True:
                if not self.rt_1.get_is_high():
                    r += 0.01
            else: # selt.t1 is low
                if self.rt_1.get_is_high():
                    r -= 0.01

            if self.t2 == True:
                if not self.rt_2.get_is_high():
                    r += 0.01
            else: # self.t2 is low
                if self.rt_1.get_is_high():
                    r -= 0.01

            self._set_rewards(r)

            # set gross-error
            e = 0.0

            if self.t1 != self.rt_1.get_is_high():
                e += 0.5

            if self.t2 != self.rt_2.get_is_high():
                e += 0.5

            self._set_gross_error(e)

    def exchange(self):
        if self._t_wait >= 0.0:
            self._train_exchange()
        else:
            self._tune_exchange()


#tog_11 = TogglePulsar(magnitude=10.0, frequency=13.0)
#tog_12 = TogglePulsar(magnitude=15.0, frequency=10.0)
#tog_13 = TogglePulsar(magnitude=20.0, frequency=7.0)
#
#tog_21 = TogglePulsar(magnitude=10.0, frequency=13.0)
#tog_22 = TogglePulsar(magnitude=15.0, frequency=10.0)
#tog_23 = TogglePulsar(magnitude=20.0, frequency=7.0)

tog_11 = VariableStochasticPulsar(magnitude=11.0, low_frequency=4.0, high_frequency=14.0)
tog_12 = VariableStochasticPulsar(magnitude=11.0, low_frequency=4.0, high_frequency=14.0)
tog_13 = VariableStochasticPulsar(magnitude=11.0, low_frequency=4.0, high_frequency=14.0)

tog_21 = VariableStochasticPulsar(magnitude=11.0, low_frequency=4.0, high_frequency=14.0)
tog_22 = VariableStochasticPulsar(magnitude=11.0, low_frequency=4.0, high_frequency=14.0)
tog_23 = VariableStochasticPulsar(magnitude=11.0, low_frequency=4.0, high_frequency=14.0)

ex_11 = NoisySpikingNeuron(threshold=50.0, magnitude=50.0, leak_eql=0.0, leak_tau=0.25)
ex_12 = NoisySpikingNeuron(threshold=50.0, magnitude=50.0, leak_eql=0.0, leak_tau=0.25)
ex_13 = NoisySpikingNeuron(threshold=50.0, magnitude=50.0, leak_eql=0.0, leak_tau=0.25)

ex_21 = NoisySpikingNeuron(threshold=50.0, magnitude=50.0, leak_eql=0.0, leak_tau=0.25)
ex_22 = NoisySpikingNeuron(threshold=50.0, magnitude=50.0, leak_eql=0.0, leak_tau=0.25)
ex_23 = NoisySpikingNeuron(threshold=50.0, magnitude=50.0, leak_eql=0.0, leak_tau=0.25)

rt_1 = RateTracker(low_threshold=5, high_threshold=10, window=0.5)
rt_2 = RateTracker(low_threshold=5, high_threshold=10, window=0.5)

mg = Manager(rt_1, rt_2, switch_wait=4.0, reward_wait=1.0)
mg.add_1_togglable(tog_11)
mg.add_1_togglable(tog_12)
mg.add_1_togglable(tog_13)
mg.add_2_togglable(tog_21)
mg.add_2_togglable(tog_22)
mg.add_2_togglable(tog_23)

#for n in [ex_11, ex_12, ex_13, ex_21, ex_22, ex_23]:
#    mg.add_gross_error_tracker(n)

entities = [tog_11, tog_12, tog_13, tog_21, tog_22, tog_23,
            ex_11, ex_12, ex_13, ex_21, ex_22, ex_23, rt_1, rt_2, mg]

# connect each toggle to each excitatory neuron, using random weights
for t in [tog_11, tog_12, tog_13, tog_21, tog_22, tog_23]:
    for e in [ex_11, ex_12, ex_13, ex_21, ex_22, ex_23]:
        w = random.uniform(0.3, 1.7)
        syn = DopamineStdp.DopamineStdpSynapse.connect(source=t, target=e, delay=0.0, efficiency=w, min_efficiency=0.3, max_efficiency=1.7, reward_manager=mg)
        entities.append(syn)

#for t in [tog_11, tog_12, tog_13]:
#    for e in [ex_11, ex_12, ex_13]:
#        w = random.uniform(0.3, 1.7)
#        syn = DopamineStdp.DopamineStdpSynapse.connect(source=t, target=e, delay=0.0, efficiency=w, min_efficiency=0.3, max_efficiency=1.7, reward_manager=mg)
#        entities.append(syn)
#
#for t in [tog_21, tog_22, tog_23]:
#    for e in [ex_21, ex_22, ex_23]:
#        w = random.uniform(0.3, 1.7)
#        syn = DopamineStdp.DopamineStdpSynapse.connect(source=t, target=e, delay=0.0, efficiency=w, min_efficiency=0.3, max_efficiency=1.7, reward_manager=mg)
#        entities.append(syn)

# connect each excitatory neuron to each rate tracker, with non-plastic synapses (weight is random, to drive asymmetry)
#for e in [ex_11, ex_12, ex_13, ex_21, ex_22, ex_23]:
#    for r in [rt_1, rt_2]:
#        w = random.uniform(0.3, 1.7)
#        syn = SnnBase.Synapse.connect(source=e, target=r, delay=0.0, efficiency=w)
#        entities.append(syn)

for e in [ex_11, ex_12, ex_13]:
    w = random.uniform(0.3, 1.7)
    syn = SnnBase.Synapse.connect(source=e, target=rt_1, delay=0.0, efficiency=w)
    syn.tau_c = 1.0 #NOTE: make tau for tags a lot faster, so we're not using data from 10 seconds ago in the tag but not in the manager
    entities.append(syn)

for e in [ex_21, ex_22, ex_23]:
    w = random.uniform(0.3, 1.7)
    syn = SnnBase.Synapse.connect(source=e, target=rt_2, delay=0.0, efficiency=w)
    syn.tau_c = 1.0
    entities.append(syn)

def pr_stren(t):
    for s in entities:
        if type(s) == DopamineStdp.DopamineStdpSynapse:
            print("{}: {}".format(t, s.efficiency))
            return

ofile = open("rs_2.dat", "w")
def pr_stren_all(t):
    ofile.write("{:3f} :  ".format(t))

    for e in entities:
        if type(e) == DopamineStdp.DopamineStdpSynapse:
            ofile.write("{:3f} ".format(e.efficiency))

    ofile.write("\n")

def pr_status(t):
    s = "{:2f}:  [{} {}]  =>  {} {}".format(t, mg.t1, mg.t2, rt_1.get_is_high(), rt_2.get_is_high())
    print(s)

cm = CallbackManager(freq=5.0)
#cm.add_callback(lambda t: print("{}".format(t)))
cm.add_callback(pr_status)
cm.add_callback(pr_stren_all)
entities.append(cm)

SnnBase.run_simulation(900.0, 1.0 / 1200.0, entities)

ofile.close()

