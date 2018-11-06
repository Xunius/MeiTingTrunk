'''A simple fuzzy logic implementation

Author: guangzhi XU (xugzhi1987@gmail.com; guangzhi.xu@outlook.com)
Update time: 2018-11-06 21:44:28.
'''

import numpy as np


def FCUp(a,b,x):
    '''Left half of a triangular membership func'''
    if abs(b-a)<=np.finfo(float).eps:
        return (x>a).astype('float')
    a,b,x=map(lambda x: np.asarray(x,dtype='float'),[a,b,x])
    y=(x-a)/(b-a)
    return np.fmin(np.fmax(0,y),1)


def FCDown(a,b,x):
    '''Right half of a triangular membership func'''
    return 1.-FCUp(a,b,x)


def FCTria(a,b,c,x):
    '''Triangular membership func'''
    a,b,c=np.sort([a,b,c])
    y=FCUp(a,b,x)*FCDown(b,c,x)
    return np.fmin(np.fmax(0,y),1)


def FCInvTria(a,b,c,x):
    return 1.-FCTria(a,b,c,x)


def FCTrap(a,b,c,d,x):
    '''Trapezoid membership func'''
    a,b,c,d=np.sort([a,b,c,d])
    y=FCUp(a,b,x)*FCDown(c,d,x)
    return np.fmin(np.fmax(0,y),1)


def FCInvTrap(a,b,c,d,x):
    return 1.-FCTrap(a,b,c,d,x)

