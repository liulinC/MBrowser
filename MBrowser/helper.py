# -*- coding: utf-8 -*-
# !/usr/bin/env python3

import asyncio
import logging
import math
import sys

from MBrowser.Const import *
from MBrowser.Session import Session

__all__ = ['waitFor']


def dictToObject(d):
    if d.get(METHOD):
        resultObj = type(d.get(METHOD), (object,), d)
    else:
        return d
    seqs = tuple, list, set, frozenset
    logging.info('PARAMS {}'.format(d.get(PARAMS)))
    if d.get(PARAMS):
        for key, value in d.get(PARAMS).items():
            logging.info('key is {}'.format(key))
            if isinstance(value, dict):
                setattr(resultObj, key, value)
            elif isinstance(value, seqs):
                setattr(resultObj, key, type(value)(dictToObject(sj) if isinstance(sj, dict) else sj for sj in value))
            else:
                setattr(resultObj, key, value)
    return resultObj


async def waitFor(breakfunction: object, timeout: int = TIMEOUT_S):
    if timeout <= 0:
        raise ValueError('time out should >0')
    loop = asyncio.get_event_loop();
    end_time = loop.time() + timeout
    while True:
        if loop.time() >= end_time:
            raise TimeoutError('time out for waitfor: {}'.format(sys._getframe().f_back.f_code.co_name))
            break
        if breakfunction():
            break
        await asyncio.sleep(0.1)


def getExceptionMessage(exceptionDetails: dict) -> str:
    exception = exceptionDetails.get('exception')
    if exception:
        return exception.get('description')
    message = exceptionDetails.get('text', '')
    stackTrace = exceptionDetails.get('stackTrace', dict())
    if stackTrace:
        for callframe in stackTrace.get('callFrames'):
            location = (callframe.get('url', '') + ':' +
                        callframe.get('lineNumber', '') + ':' +
                        callframe.get('columnNumber'))
            functionName = callframe.get('functionName', '<anonymous>')
            message = message + f'\n    at {functionName} ({location})'
    return message


def valueFromRemoteObject(remoteObject):
    if remoteObject.get('unserializableValue'):
        if remoteObject.get('unserializableValue') == '-0':
            return -0
        if remoteObject.get('unserializableValue') == 'NaN':
            return None
        if remoteObject.get('unserializableValue') == 'Infinity':
            return math.inf
        if remoteObject.get('unserializableValue') == '-Infinity':
            return -math.inf
        raise RuntimeError('nsupported unserializable value: {}'.format(remoteObject.get('unserializableValue')))
    return remoteObject.get('value')


async def releaseObject(client: Session, remoteObject: dict) -> None:
    objectId = remoteObject.get('objectId')
    if not objectId:
        return
    try:
        await client.send('Runtime.releaseObject', dict(objectId=objectId))
    except:
        pass
