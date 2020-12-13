from numpy import polyfit
from math import log as LOG


def getArray(dict, key):
    return list(map(dict, key))


def trend(Y, X, x):
    # print(Y,X,x)
    sY = sX = sYX = sX2 = 0
    N = len(X)
    for n in range(N):
        sY += Y[n]
        sX += X[n]
        sYX += X[n] * Y[n]
        sX2 += X[n] ** 2
    den = 1 / (N * sX2 - sX ** 2)
    return den * ((N * sYX - sY * sX) * x + (sY * sX2 - sYX * sX))


def linest(y, x, p):
    return polyfit(x, y, p)
