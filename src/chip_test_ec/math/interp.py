# -*- coding: utf-8 -*-

from scipy.interpolate import InterpolatedUnivariateSpline
from sklearn.isotonic import IsotonicRegression


def monotonize(xvec, yvec):
    """Find the array closest to yvec in the least-square sense that is monotonic."""
    reg = IsotonicRegression(increasing='auto')
    yvec_mono = reg.fit_transform(xvec, yvec)
    return yvec_mono


def monotonic_linear(xvec, yvec):
    """Returns a monotonic linear function that interpolates the given data points."""
    reg = IsotonicRegression(increasing='auto')
    yvec_mono = reg.fit_transform(xvec, yvec)
    x_list, y_list = [], []
    if yvec_mono[-1] < yvec_mono[0]:
        yvec_mono = yvec_mono[::-1]
        xvec = xvec[::-1]

    for x, y, in zip(xvec, yvec_mono):
        if not x_list or y != y_list[-1]:
            x_list.append(x)
            y_list.append(y)

    if x_list[0] > x_list[-1]:
        x_list = x_list[::-1]
        y_list = y_list[::-1]
    return InterpolatedUnivariateSpline(x_list, y_list, k=1, ext='extrapolate')
