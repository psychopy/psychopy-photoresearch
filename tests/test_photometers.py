#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for photometers manufactured by Photo Research Inc.
"""

# Originally from the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

import psychopy.logging as logging
import psychopy.hardware as hardware  # use the stub in PsychoPy lib
import pytest

logging.console.setLevel(logging.DEBUG)


def test_PR655():
    """Tests for the PR655 photometer manufactured by Photo Research Inc.

    Requires a physical device to be connected to the system. Device is found
    using the `~psychopy.hardware.findPhotometer` routine.

    """
    pr655 = hardware.findPhotometer(device='PR655')
    if pr655 is None:
        logging.warning('Cannot test PR655 interface, no device found.')
    else:
        print(('type:', pr655.type))
        print(('SN:', pr655.getDeviceSN()))
        # on linux we do actually find a device that returns 'D'
        if pr655.type == 'D':
            pytest.skip()

        # get values and print them
        pr655.measure()
        nm, spec = pr655.getLastSpectrum()
        print(('lum:', pr655.lastLum))
        print(('uv:', pr655.lastUV))
        print(('xy:', pr655.lastXY))
        print(('tristim:', pr655.lastTristim))
        print(('nm:', nm))
        print(('spec:', spec))
        print(('temperature:', pr655.lastColorTemp))
