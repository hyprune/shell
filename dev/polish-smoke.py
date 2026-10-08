#!/usr/bin/env python3
"""Run hyprune-dev's legacy smoke with current TAB hold timing, under flock.
No core source changes; all its original acceptance assertions remain in place.
"""
import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR', str(ROOT.parent / 'core')))
sys.path.insert(0, str(CORE / 'dev/nested'))
import session
import integration

original_keys = integration.keys

def keys(*args):
    if args == ('-P', 'Tab', '-s', '500', '-p', 'Tab'):
        args = ('-P', 'Tab', '-s', '1150', '-p', 'Tab')
    return original_keys(*args)

integration.keys = keys
integration.STATE = session.HERE / '.integration-state'
session.run(argparse.Namespace(integration=True, m3b=False, m3a=False,
    m2=False, m1=False, live=False, serve=False, record=False, visible=False))
