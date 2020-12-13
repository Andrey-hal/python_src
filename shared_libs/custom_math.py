import numpy as np
from math import pi

def trend(Y, X, x):
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
    return np.polyfit(x, y, p)


def trigger_work_area(x, y,  point, up, down, left, right, d=3):
    if type(x) is dict:
        x = x.values()
    if type(y) is dict:
        y = y.values()
    result = {"up": True, "down": True, "left": True, "right": True}
    poly_cof = linest(y, x, d)
    f = np.poly1d(poly_cof)
    y_must_be = f(point["x"])
    # print(y_must_be, point['y'], (y_must_be + y_must_be * up["p"] + up["c"]))
    if point["y"] > (y_must_be + y_must_be * up["p"] + up["c"]):
        result["up"] = False

    elif point["y"] < (y_must_be - y_must_be * down["p"] + down["c"]):
        result["down"] = False
    max_x = max(x)
    min_x = min(x)
    if point["x"] > (max_x + max_x * right["p"] + right["c"]):
        result["right"] = False
    elif point["x"] < (min_x - min_x * left["p"] + left["c"]):
        result["left"] = False
    return all(result.values())

def PI():
    return pi


def approx(X, Y, x, p):
    return np.poly1d(np.polyfit(X, Y, p))(x)


