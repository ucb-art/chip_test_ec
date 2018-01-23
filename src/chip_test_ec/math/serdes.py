# -*- coding: utf-8 -*-

import scipy.misc
import scipy.optimize


def _get_ber_probability(ntot, nerr, ber):
    """Calculate probability of getting exactly nerr errors in ntot bits given BER."""
    return scipy.misc.comb(ntot, nerr) * ber**nerr * (1-ber)**(ntot-nerr)


def get_ber_exact(confidence, ntot, nerr, tol):
    targ_val = 1 - confidence

    def fun(p):
        s = 0
        for k in range(nerr + 1):
            s += _get_ber_probability(ntot, k, p)
        return s - targ_val

    return scipy.optimize.brentq(fun, 0, 0.5, xtol=tol)


def get_ber_list(confidence, ntot, nerr_max, tol):
    """Get a list of pre-computed BER values"""
    return [get_ber_exact(confidence, ntot, nerr, tol) for nerr in range(nerr_max + 1)]


def get_ber(confidence, ntot, nerr):
    if nerr <= 10:
        return get_ber(confidence, ntot, nerr)
    else:
        return nerr / ntot
