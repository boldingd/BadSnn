#! /usr/bin/python3

import SnnBase
import Stdp
import DopamineStdp

import random


#NOTE: I just added a TotalErrorMessenger, badly
#      I should go back and do that right.  Or find a better solution.


#class SymmetricStdpSynapse:
#    def __init__(self, delay, efficiency, min_efficiency, max_efficiency, window):
#        self.delay = delay
#        self.min_efficiency = min_efficiency
#        self.max_efficiency = max_efficiency
#        
#        self.efficiency = efficiency
#        
#        self.window = window
#
#        self.T = None
#        
#        self.waiting_spikes = []
#        self.outgoing_spikes = []
#        
#        self.targets = []
#        
#        self.efficiency_update = 0.0        
#        
#    def add_spike(self, magnitude):
#        self.efficiency_update += (1.0 / math.cosh(self.T)) - 0.5 # sech(x) - 0.5
#        self.T += self.A_t
#            
#        ds = SnnBase.DelayedSpike(self.delay, magnitude)
#        
#        self.waiting_spikes.append(ds)
#    
#    def add_target(self, target):
#        self.targets.append(target)
#        
#    def get_sample(self):
#        return self.efficiency
#        
#    def notify_of_spike(self):
#        self.efficiency_update += (1.0 / math.cosh(self.T)) - 0.5 # sech(x) - 0.5
#        
#    def prepare(self):
#        # apply efficiency change from last cycle before step / exchange
#        if self.efficiency_update != 0.0:
#            self.efficiency += self.efficiency_update
#            
#            # clip to allowed range
#            if self.efficiency > self.max_efficiency:
#                self.efficiency = self.max_efficiency
#            elif self.efficiency < self.min_efficiency:
#                self.efficiency = self.min_efficiency
#                
#            self.efficiency_update = 0.0
#            
#    def step(self, dt):        
#        # M and P exponentially decay to 0
#        delta_T = -1.0 * self.T * (dt / self.tau_t)
#        self.T += delta_T
#        
#        # spike, as basic delayed neuron
#        temp_spikes = self.waiting_spikes
#        self.waiting_spikes = []
#        self.outgoing_spikes = []
#
#        for spike in temp_spikes:
#            spike.remaining_delay -= dt
#            
#            if spike.remaining_delay <= 0.0:
#                self.outgoing_spikes.append(spike)
#            else:
#                self.waiting_spikes.append(spike)
#                
#    def exchange(self):
#        for s in self.outgoing_spikes:
#            for t in self.targets:
#                t.add_spike(self.efficiency * s.magnitude)
#                
#    @staticmethod
#    def connect(source, target, delay, efficiency, min_efficiency, max_efficiency):
#        s = InhibitoryStdpSynapse(delay, efficiency, min_efficiency, max_efficiency)
#        
#        s.add_target(target)
#        source.add_synapse(s)
#        
#        target.add_spike_listener(s)
#        
#        return s


###
### on third thought, I'm not sure I like the idea of having multiple r-signals, one per output neuron.
### if the network needs that, it cuts into the whole point.
###
##
### quick re-evaluation
### must be a separate entity from the neuron, since the neuron will synapse with multiple other neurons.
### if it must be separate, we should preserve order-independance, which basically means we still have to hold all spikes for (at least) one tick.
### soooo the only simplifications I can really make is stepping back to exacty one-tick delay and reducing myself to exactly one target.
### which doesn't really change the design that much
##
### implicit assumptions:
### we will get updates from mod-sources during Exchange, and apply them next-step
### change: we will explicitly get our mod signals during step, assuming a global thing computes them during the previous exchange.
### is that /actually/ either cleaner or faster?
### no, I don't think it is.  And it violates the "no communication during step" rule.
##class RewardSignalSynapse:
##    def __init__(self, efficiency, min_efficiency, max_efficiency, target=None):
##        self.min_efficiency = min_efficiency
##        self.max_efficiency = max_efficiency
##
##        self.efficiency = efficiency
##
##        self.M = 0.0
##        self.A_m = -0.015 # minor notation change
##        self.tau_m = 0.0025
##
##        self.P = 0.0
##        self.A_p = 0.015
##        self.tau_p = 0.0025
##
##        self.waiting_spikes = [] # TODO: these don't need to be lists, since I think we'll only ever get one spike per tick -- SNs shouldn't ever spike twice in a tick.  But I can adjust that later.
##        self.outgoing_spikes = []
##
##        self.target = target
##
##        self.c = 0.0
##        self.tau_c = 15.0 # very slow time-dynamics
##        
##        self.mod_accm = 0.0
##
##    def add_spike(self, magnitude):
##        self.P += self.A_p
##        self.c += self.M * self.max_efficiency
##
##        self.waiting_spikes.append(magnitude)
##
##    def set_target(self, target):
##        if self.target is None:
##            raise SnnBase.SnnError("RewardSignalSynapse does not support changing target after target has been set.")
##
##        self.target = target
##
##    def notify_of_spike(self):
##        self.M += self.A_m
##        self.c += self.P * self.max_efficiency
##
##    def step(self, dt):
##        self.efficiency += self.mod_accm * self.c * dt
##        self.mod_accm = 0.0
##
##        # clamp to allowed range
##        if self.efficiency > self.max_efficiency:
##            self.efficiency = self.max_efficiency
##        elif self.efficiency < self.min_efficiency:
##            self.efficiency = self.min_efficiency
##
##        self.c += -1.0 * self.c * (dt / self.tau_c)
##
##        self.M += -1.0 * self.M * (dt / self.tau_m)
##
##        self.P += -1.0 * self.P * (dt / self.tau_p)
##
##        # little worried this'll thrash all over my memory space
##        self.outgoing_spikes = self.waiting_spikes
##        self.waiting_spikes = []
##
##    def exchange(self):
##        for s in self.outgoing_spikes:
##            self.target.add_spike(self.efficiency * s)
##
##    def add_mod_incr(self, incr):
##        self.mod_accm += incr
##
##    @staticmethod
##    def connect():
##        pass


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
            #self.rand_val = random.uniform(-1.0, 1.0)
            self.err_eql = random.choice([self.max_efficiency, self.min_efficiency])

#        n = random.uniform(-1, 1)
#        self.efficiency += self.total_abs_error * n * dt
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


###########
# A B | A B
# ---------
# T T | F T
# T F | T F
# F T | F F
# F F | F F
###########

#def Rule(state):
#    if state[0] == True and state[1] == True:
#        return (False, True)
#    elif state[0] == True and state[1] == False:
#        return (True, False)
#    elif state[0] == False and state[1] == True:
#        return (False, False)
#    elif state[0] == False and state[1] == False:
#        return (False, False)
#    else: # unreachable, unless someone puts something not True or False in the tuple
#        print(">>>   " + str(state))
#        raise Exception("Argument must be two-length tuple of boolean values (it was {}).".format(type(state)))

def Rule(state):
    if state[0] == True and state[1] == True:
        return (True, True)
    elif state[0] == True and state[1] == False:
        return (True, False)
    elif state[0] == False and state[1] == True:
        return (False, True)
    elif state[0] == False and state[1] == False:
        return (False, False)
    else: # unreachable, unless someone puts something not True or False in the tuple
        print(">>>   " + str(state))
        raise Exception("Argument must be two-length tuple of boolean values (it was {}).".format(type(state)))


#class Controller:
#    def __init__(self, switch_wait, a_tracker, b_tracker):
#        self.switch_wait = switch_wait
#
#        self._cur_a = False
#        self._cur_b = False
#
#        self._a = a_tracker
#        self._b = b_tracker
#
#        self.r = 0.0
#        self.r_0 = 0.0
#        self.t_r = 0.25 # make r fast
#
#    def step(dt):
#        self.switch_wait -= dt
#        if self.switch_wait <= 0.0:
#            pass # switch
#
#        cur = (self._a.get_is_high(), self._b.get_is_high())
#        res = rule(cur)
#
#        if cur == res:
#            r_0 = 0.0 # TODO: here


class EqlRewardManager:
    def __init__(self, eql, tau):
        self.eql = eql
        self.tau = tau

        self.r = eql

        self.rewardables = []

    def set_reql(self, reql):
        self.eql = reql

    def add_rewardable(self, rewardable):
        self.rewardables.append(rewardable)

    def step(self, dt):
        self.r += (self.eql - self.r) * (dt / self.tau)

    def exchange(self):
        for rw in self.rewardables:
            rw.reward(self.r)


#  SwitchDriver sets target on ErrorManager
#  ErrorManager compares rate-counter-state to target, sets Reward
#  Everybody gets their reward from RewardManager
class ErrorManager:
    def __init__(self, r1, r2, rmanager, emanager):
        self.t1 = None
        self.t2 = None

        self.r1 = r1
        self.r2 = r2

        self.rmanager = rmanager
        self.emanager = emanager

    def notify_of_switch(self, t1, t2):
        self.t1 = t1
        self.t2 = t2

    def step(self, dt):
        pass # wow, we actually have nothing to do in this step!

    def exchange(self):
        if self.t1 is None or self.t2 is None:
            self.rmanager.set_reql(0.0)
            return

        r = 0.0

        s = (self.t1, self.t2)
        targ1, targ2 = Rule(s)
        #TODO: major to-do is the case where these cancel out
        
        #TODO: if the SwitchManager has its exchange called /after/ us, we'll be one (more) cycle delayed detecting it
        #      I could fix that by doing this in prepare.

#        # idiot!  it's an error signal
#        if self.r1.get_is_high() == self.t1:
#            r += 0.5
#        else:
#            r -= 0.5
#
#        if self.r2.get_is_high() == self.t2:
#            r += 0.5
#        else:
#            r -= 0.5

        if self.t1 == True and self.r1.get_is_high() == False:
            r += 0.5 # spike more
        elif self.t1 == False and self.r1.get_is_high() == True:
            r -= 0.5 # spike less

        if self.t2 == True and self.r2.get_is_high() == False:
            r += 0.5
        elif self.t2 == False and self.r2.get_is_high() == True:
            r -= 0.5
        
        self.rmanager.set_reql(0.15 * r) # actually only works with the EqlRewardManager


        total_error = 0.0

        if self.t1 != self.r1.get_is_high():
            total_error += 0.5

        if self.t2 != self.r2.get_is_high():
            total_error += 0.5 

        self.emanager.set_total_error(total_error)


class TotalErrorManager:
    def __init__(self):
        self.error_listeners = list()
        self.total_error = 0.0

    def set_total_error(self, total_error):
        self.total_error = total_error

    def add_error_listener(self, listener):
        self.error_listeners.append(listener)

    def step(self, dt):
        pass

    def exchange(self):
        for listener in self.error_listeners:
            listener.set_total_abs_error(self.total_error)


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

class Clock:
    def __init__(self):
        self.t = 0.0

    def step(self, dt):
        self.t += dt


class SwitchDriver:
    def __init__(self, tog_1, tog_2, track_1, track_2, window):
        self.tog_1 = tog_1
        self.tog_2 = tog_2
        self.track_1 = track_1
        self.track_2 = track_2

        self.window = window
        self._wait = window

        self._switch = False

        self._switch_listeners = []

    def step(self, dt):
        self._wait -= dt
        if self._wait <= 0.0:
            self._wait = self.window

            self._switch = True

    def add_switch_listener(self, listener):
        self._switch_listeners.append(listener)

    def exchange(self):
        if self._switch == False:
            return

        self._switch = False

        t1 = False
        t2 = False

        if random.random() < 0.5:
            self.tog_1.queue_inactivation()
        else:
            self.tog_1.queue_activation()
            t1 = True

        if random.random() < 0.5:
            self.tog_2.queue_inactivation()
        else:
            self.tog_2.queue_activation()
            t2 = True

        for listener in self._switch_listeners:
            listener.notify_of_switch(t1, t2)


ex_1 = SnnBase.SpikingNeuron(threshold=50.0, magnitude=10.0, leak_eql=0.0, leak_tau=0.5)
ex_2 = SnnBase.SpikingNeuron(threshold=50.0, magnitude=10.0, leak_eql=0.0, leak_tau=0.5)
inh  = SnnBase.SpikingNeuron(threshold=50.0, magnitude=-20.0, leak_eql=0.0, leak_tau=0.5)

rt_1 = RateTracker(high_threshold=4, low_threshold=2, window=1.0)
rt_2 = RateTracker(high_threshold=4, low_threshold=2, window=1.0)

t_1 = TogglePulsar(magnitude=30.0, frequency=15.0)
t_2 = TogglePulsar(magnitude=30.0, frequency=15.0)


#rm = DopamineStdp.RewardManager(equilibrium=0.0, tau=15.0)
rm = EqlRewardManager(0.0, 0.25) #dopamine time-dynamics are slow # ah, a major problem was that r needs to very very quickly, almost immediately.  Derp, I dumb
te = TotalErrorManager()

#syn_tog1_ex1 = DopamineStdp.DopamineStdpSynapse.connect(source=t_1, target=ex_1, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
#syn_tog2_ex1 = DopamineStdp.DopamineStdpSynapse.connect(source=t_2, target=ex_1, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
syn_tog1_ex1 = NoisyDopamineSynapse.connect(source=t_1, target=ex_1, delay=0.0, efficiency=0.7, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
te.add_error_listener(syn_tog1_ex1)
syn_tog2_ex1 = NoisyDopamineSynapse.connect(source=t_2, target=ex_1, delay=0.0, efficiency=1.3, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
te.add_error_listener(syn_tog2_ex1)
syn_ex1_rt1  = SnnBase.Synapse.connect(source=ex_1, target=rt_1, delay=0.0, efficiency=1.0)

#syn_tog1_ex2 = DopamineStdp.DopamineStdpSynapse.connect(source=t_1, target=ex_2, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
syn_tog1_ex2 = NoisyDopamineSynapse.connect(source=t_1, target=ex_2, delay=0.0, efficiency=1.3, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
te.add_error_listener(syn_tog1_ex2)
#syn_tog2_ex2 = DopamineStdp.DopamineStdpSynapse.connect(source=t_2, target=ex_2, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
syn_tog2_ex2 = NoisyDopamineSynapse.connect(source=t_2, target=ex_2, delay=0.0, efficiency=0.7, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
te.add_error_listener(syn_tog2_ex2)
syn_ex2_rt2  = SnnBase.Synapse.connect(source=ex_2, target=rt_2, delay=0.0, efficiency=1.0)

syn_ex1_inh = DopamineStdp.DopamineStdpSynapse.connect(source=ex_1, target=inh, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
syn_ex2_inh = DopamineStdp.DopamineStdpSynapse.connect(source=ex_2, target=inh, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
#syn_inh_ex1 = DopamineStdp.DopamineStdpSynapse.connect(source=inh, target=ex_1, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
#syn_inh_ex2 = DopamineStdp.DopamineStdpSynapse.connect(source=inh, target=ex_2, delay=0.0, efficiency=1.0, min_efficiency=0.3, max_efficiency=1.7, reward_manager=rm)
syn_inh_ex1 = SnnBase.Synapse.connect(source=inh, target=ex_1, delay=0.0, efficiency=1.0)
syn_inh_ex2 = SnnBase.Synapse.connect(source=inh, target=ex_2, delay=0.0, efficiency=1.0)


sd = SwitchDriver(t_1, t_2, rt_1, rt_2, 5.0)

em = ErrorManager(rt_1, rt_2, rm, te)

sd.add_switch_listener(em)

def pr_sample(t):
    print("{:5g}:  [{} {}]  =>  {} {}".format(t, t_1.get_is_active(), t_2.get_is_active(), rt_1.get_is_high(), rt_2.get_is_high()))

ofile = open("dop_syn.dat", "w")
ofile_rlvl_elvl = open("rlvl.dat", "w")


clock = Clock()
cb_manager = CallbackManager(freq=10.0)
#cb_manager.add_callback(lambda t: print("t: " + str(t)))
cb_manager.add_callback(pr_sample)
#cb_manager.add_callback(lambda t: print("{}:  {}".format(t, ex_1.get_sample())))
#cb_manager.add_callback(lambda t: print("{}:  {}".format(t, syn_ex2_inh.get_sample())))
cb_manager.add_callback(lambda t: ofile.write("{}:  {}\n".format(t, syn_ex2_inh.get_sample())))
cb_manager.add_callback(lambda t: ofile_rlvl_elvl.write("{}: {} {} {}\n".format(t, rm.r, te.total_error, syn_tog2_ex2.efficiency)))

ens = [ex_1, ex_2, inh, rt_1, rt_2, t_1, t_2, sd,
       syn_tog1_ex1, syn_tog2_ex1, syn_ex1_rt1, syn_tog1_ex2, syn_tog2_ex2, syn_ex2_rt2,
       syn_ex1_inh, syn_ex2_inh, syn_inh_ex1, syn_inh_ex2,
       rm, em, te,
       clock, cb_manager]
SnnBase.run_simulation(500.0, 1.0 / 1200.0, ens)


ofile.close()
ofile_rlvl_elvl.close()

