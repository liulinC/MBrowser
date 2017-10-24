# -*- coding: utf-8 -*-

import json
import logging
import math
from typing import Any

from MBrowser import helper
from MBrowser.Const import *
from MBrowser.EventEmitter import EventEmitter

__all__ = ['ExecutionContext', 'JSHandle']


class ExecutionContext(EventEmitter):
    def __init__(self, client, contextId, objectHandleFactory):
        self._client = client
        self._contextId = contextId
        self._objectHandleFactory = objectHandleFactory
        self._log = logging.getLogger('ExecutionContext.ExecutionContext')

    async def evaluate(self, pageFunction: str, *args: Any):
        handle = await self.evaluateHandle(pageFunction, *args)
        result = await handle.jsonValue()
        await handle.dispose()
        return result

    async def _funEvaluate(self, pageFunction: str, returnByValue: bool = False, awaitPromise: bool = True):
        contextId = self._contextId
        expression = pageFunction
        resp = await self.emit(SE, 'Runtime.evaluate', dict(expression=expression, contextId=contextId,
                                                            returnByValue=returnByValue,
                                                            awaitPromise=awaitPromise), waitRspAndReturn=True)

        if resp.get(RESULT).get('exceptionDetails'):
            self._log.error('get a ERROR rsp {}'.format(resp.get(RESULT).get('exceptionDetails')))
            raise RuntimeError('get a ERROR rsp {}'.format(resp.get(RESULT).get('exceptionDetails')))
        return resp.get(RESULT).get(RESULT)

    async def _callFunctionOn(self, pageFunction: str, objectid: str, *args: Any, returnByValue: bool = False,
                              awaitPromise: bool = True):
        arglist = [self.convertArgument(arg) for arg in args]
        result = await self.emit(SE, 'Runtime.callFunctionOn', dict(functionDeclaration=str(pageFunction),
                                                                    objectId=objectid,
                                                                    arguments=arglist,
                                                                    returnByValue=returnByValue,
                                                                    awaitPromise=awaitPromise), waitRspAndReturn=True)

        if result.get(RESULT).get('exceptionDetails'):
            self._log.error('get a ERROR rsp {}'.format(result.get(RESULT).get('exceptionDetails')))
            return None
        return result.get(RESULT).get(RESULT)

    async def evaluateHandle(self, pageFunction: str, *args: Any, returnByValue: bool = False,
                             awaitPromise: bool = True):
        result = await self._funEvaluate(pageFunction, returnByValue=returnByValue, awaitPromise=awaitPromise)
        self._log.info('Evaluate result was {}'.format(result))

        if result.get(OBID) and result.get('type') == 'function':
            result = await self._callFunctionOn(pageFunction, result.get(OBID),
                                                *args, returnByValue=returnByValue, awaitPromise=awaitPromise)
            self._log.info('CallFunctionOn result {}'.format(result))
            return self._objectHandleFactory(self._contextId, result)
        else:
            return result

    def convertArgument(self, arg: Any):
        if arg is 0:
            return {'unserializableValue': '-0'}
        if arg == -0:
            return {'unserializableValue': '-0'}
        if arg == math.inf:
            return {'unserializableValue': 'Infinity'}
        if arg == -math.inf:
            return {'unserializableValue': '-Infinity'}
        if arg == None:
            return {'unserializableValue': 'NaN'}
        if isinstance(arg, JSHandle):
            if arg._disposed:
                raise RuntimeError('JSHandle has disposed')
            if arg._context != self:
                raise RuntimeError('JSHandles can be evaluated only in the context they were created!')
            objectId = arg._remoteObject.get(OBID)
            if not objectId:
                return {'value': arg._remoteObject.get('value')}
            return {'objectId': objectId}
        return {'value': arg}

    async def queryObjects(self, prototypeHandle):
        assert not prototypeHandle._disposed, 'Prototype JSHandle is disposed!'
        assert prototypeHandle._remoteObject.get(OBID), 'Prototype JSHandle must not be referencing primitive value'
        response = await self._client.send('Runtime.queryObjects', {
            'prototypeObjectId': prototypeHandle._remoteObject.get(OBID)
        })
        return self._objectHandleFactory(self._contextId, response.get('objects'))


class JSHandle(object):
    def __init__(self, log, context: ExecutionContext, client: object, remoteObject: dict, page: object):
        self._log = log
        self._context = context
        self._client = client
        self._remoteObject = remoteObject
        self._disposed = False
        self._page = page

    def executionContext(self):
        return self._context

    async def getProperty(self, propertyName: dict):
        objectHandle = await self._context.evaluateHandle('''(object, propertyName) => {
          result = {__proto__: null}
          result[propertyName] = object[propertyName]
          return result
        }''', self, propertyName)
        properties = await objectHandle.getProperties()
        result = properties.get(propertyName) or None
        await objectHandle.dispose()
        return result

    async def getProperties(self):
        response = await self._client.send('Runtime.getProperties', dict(
            objectId=self._remoteObject.get(OBID),
            ownProperties=True
        ))
        result = {}
        for property in response.get(RESULT):
            if not property.enumerable:
                continue
            result[property.name] = self._context._objectHandleFactory(self._context, property.value)

        return result

    async def jsonValue(self):
        if self._remoteObject.get(OBID):
            jsonString = await self._context.evaluate(r'object => JSON.stringify(object)', self)
            return json.loads(jsonString)
        return helper.valueFromRemoteObject(self._remoteObject)

    def asElement(self):
        return None

    async def dispose(self):
        if self._disposed:
            return None
        self._disposed = True
        await helper.releaseObject(self._client, self._remoteObject)

    def toString(self):
        if self._remoteObject.get(OBID):
            type = self._remoteObject.get('subtype') or self._remoteObject.get('type')
            return 'JSHandle@' + type
        return 'JSHandle:' + helper.valueFromRemoteObject(self._remoteObject)
