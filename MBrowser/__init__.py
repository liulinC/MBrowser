# -*- coding: utf-8 -*-

import logging

__author__ = '''hongjie Zheng'''
__email__ = 'hongjie0923@gmail.com'
__version__ = '0.0.1'


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s:  %(message)s')

logger = logging.getLogger('MBROWSER')



from MBrowser.Browser import Browser
from MBrowser.ElementHandle import ElementHandle
from MBrowser.EventEmitter import EventEmitter
from MBrowser.EventLoop import execute, create_task,create_future
from MBrowser.ExecutionContext import ExecutionContext, JSHandle
from MBrowser.FrameManager import Frame, FrameManager
from MBrowser.helper import waitFor
from MBrowser.Input import Keyboard, Mouse, Touchscreen
from MBrowser.Launcher import Launcher
from MBrowser.Pages import Page
from MBrowser.Session import Session

__all__ = ['Browser', 'ElementHandle', 'EventEmitter', 'execute', 'create_task', 'create_future',
           'ExecutionContext', 'JSHandle', 'Frame', 'FrameManager', 'waitFor', 'Keyboard', 'Mouse',
           'Touchscreen', 'Launcher', 'Page', 'Session']

