# -*- coding: utf-8 -*-

"""This module defines a MetricSpinBox, a subclass of QDoubleSpinBox that use metric prefixes."""

import numpy as np
import PyQt4.QtGui as QtGui


prefix_names = ['y', 'z', 'a', 'f', 'p', 'n', 'u', 'm', '',
                'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
prefix_exp = [-24, -21, -18, -15, -12, -9, -6, -3, 0,
              3, 6, 9, 12, 15, 18, 21, 24]


class MetricSpinBox(QtGui.QDoubleSpinBox):
    def __init__(self, vmin, vmax, vstep, precision):
        """Create a new MetricSpinBox instance.

        Parameters
        ----------
        vmin : float
            the minimum value.
        vmax : float
            the maximum value.
        vstep : float
            the step size of the MetricSpinBox.
        precision : int
            the displayed precision.
        Returns
        -------

        """
        super(MetricSpinBox, self).__init__()
        exp = int(np.floor(np.log10(vstep)))
        if exp < prefix_exp[0] or exp > prefix_exp[-1]:
            prefix = 'e{}'.format(exp)
            self.scale = 10.0**exp
        elif exp in prefix_exp:
            prefix = prefix_names[prefix_exp.index(exp)]
            self.scale = 10.0**exp
        else:
            idx = None
            for i in xrange(len(prefix_exp)):
                if prefix_exp[i + 1] > exp:
                    idx = i + 1
                    break
            prefix = prefix_names[idx]
            diff = prefix_exp[idx] - exp
            precision = max(precision, diff)
            self.scale = 10.0**prefix_exp[idx]

        vstep = int(np.round(vstep / self.scale * 10.0**precision)) * 10.0**(-precision)
        vmin /= self.scale
        vmax /= self.scale
        self.setSingleStep(vstep)
        self.setMinimum(vmin)
        self.setMaximum(vmax)
        self.setDecimals(precision)
        self.setSuffix(' ' + prefix)

    def value(self):
        val = super(MetricSpinBox, self).value()
        return val * self.scale

    def setValue(self, val):
        super(MetricSpinBox, self).setValue(val / self.scale)
