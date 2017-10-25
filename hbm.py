#! /usr/bin/python3

import numpy
import scipy
import random


class HarrisonMachine:
    def __init__(self, visible, hidden, lr):
        self.i = visible
        self.j = hidden

        self.W = numpy.random.uniform(-1.0, 1.0, (self.j, self.i))

        self.lr = lr

        self.v_bias = numpy.random.uniform(-1.0, 1.0, (self.i, 1))
        self.h_bias = numpy.random.uniform(-1.0, 1.0, (self.j, 1))

    def update(self, v):
        #h = self._get_h(v, return_probs=False)

        h_probs = self.W @ v
        h = probs_to_signs(h_probs)
        h *= -1.0

        #h, e = self._get_h(v)

        for j in range(self.j):
            for i in range(self.i):
                ep = self.W[j,i] * h[j] * v[i]
                
                sign = h[j] * v[i]

                damp = -1.0 * numpy.tanh(ep)
                #em = -ep
                #fp = numpy.exp(ep)
                #fm = numpy.exp(em)
                #damp = - (fp - fm) / (fp + fm)
                # didn't make a damned difference, just like it shouldn't have

                if sign > 0:
                    damp = -damp

                self.W[j, i] -= (sign + damp) * self.lr
    
    # def _get_h(self, v, return_probs=False):
    #     h = self.W @ v # Jesus, is there not even a nonlinearity?
        
    #     if not return_probs:
    #         rh = numpy.random.uniform(0.0, 1.0, (self.j, 1))
    #         for j in range(self.j): # prob <= rand  ==  rand > prob
    #             if h[j] <= rh[j]:
    #                 h[j] = 1.0
    #             else:
    #                 h[j] = -1.0

    #     return h

    def _get_h(self, v):
        h = numpy.zeros((self.j,1))
        e = 0.0

        for j in range(self.j): # for each hidden node
            ep = 0.0
            em = 0.0

            for i in range(self.i): # for each visible node
                # add positive and negative e
                ep += v[i] * self.W[j,i] * 1.0
                em += v[i] * self.W[j,i] * -1.0

            # this looks backward, but it's what he's got
            if em < ep:
                e += em
                h[j] = -1.0
            else:
                e += ep
                h[j] = 1.0

        return (h, e)

    # hell, this is probably wrong too
    def sample_step(self, v):
        #h_probs = self._get_h(v, return_probs=False)
        h_probs = self.W @ v
        h_signs = probs_to_signs(h_probs)

        v_probs = self.W.T @ h_signs

        return probs_to_signs(v_probs)

def probs_to_signs(probs):
    res = numpy.ones(probs.shape)
    rands = numpy.random.random(probs.shape)
    
    for r in range(len(res)): # won't work if it's 2D
        if rands[r] > probs[r]:
            res[r] = -1.0

    return res 


def test():
    hbm = HarrisonMachine(6, 3, lr=0.05)

    p1 = numpy.array([
        [1.0],
        [-1.0],
        [1.0],
        [-1.0],
        [-1.0],
        [-1.0]
    ])
    
    # p2 = numpy.zeros((5,1))
    # p2[0,0] = 1.0
    # p2[4,0] = 1.0

    p2 = numpy.array([
        [-1.0],
        [-1.0],
        [1.0],
        [-1.0],
        [1.0],
        [-1.0]
    ])

    # p3 = numpy.zeros((5,1))
    # p3[2,0] = 1.0
    # p3[4,0] = 1.0

    p3 = numpy.array([
        [1.0],
        [-1.0],
        [-1.0],
        [-1.0],
        [1.0],
        [-1.0]
    ])

    data = [p1, p2, p3]

    for _ in range(50000):
        sample = random.choice(data)

        hbm.update(sample)

    #for _ in range(10):
    #    v = numpy.random.random((6,1))

    print(str(hbm.W))

    for i in range(10):
        print("reconstruction {}".format(i))
        state = numpy.random.uniform(-1.0, 1.0, p1.shape)
        print(str(state))
        print(str( state.T @ state ))
        for _ in range(20):
            state = hbm.sample_step(state)
        print(str(state))

        print("\n")

if __name__ == "__main__":
    test()


# something fucky is happening, because I just noticed that my _get_h has been backwards-
# as the probs go up, the odds of actually getting +1 go down.
# and yet that is the version that works, the "correct" version doesn't.
# this might also be tied up with why I sometimes get the inverse of a pattern