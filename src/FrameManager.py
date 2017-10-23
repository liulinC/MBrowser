# -*- coding: utf-8 -*-

import logging

from .Const import *
from .ElementHandle import ElementHandle
from .EventEmitter import EventEmitter
from .ExecutionContext import ExecutionContext, JSHandle


class FrameManager(EventEmitter):
    def __init__(self, client, page):
        self._log = logging.getLogger('FrameManager.FrameManager')
        self._client = client
        self._page = page

        self._frames = {}
        self._contextIdToContext = {}
        self._events = [Page_frameAttached,
                        Page_frameNavigated,
                        Page_frameDetached,
                        Runtime_executionContextCreated]
        self.on(self._events, self._processEvent)
        self._mainFrame = None

    def mainFrame(self):
        if self._mainFrame == None:
            self._log.warning('mainframe is None')
        return self._mainFrame

    def frames(self):
        return self._frames.values()

    async def _processEvent(self, *arg, **Kargs):
        (event_name, event) = arg
        if event_name == Page_frameNavigated:
            self._onFrameNavigated(event.get('frame'))
        if event_name == Page_frameAttached:
            self._onFrameAttached(event.get('frame').get('id'), event.get('frame').get('parentFrameId'))
        if event_name == Page_frameDetached:
            self._onFrameDetached(event.frame.id)
        if event_name == Runtime_executionContextCreated:
            self._onExecutionContextCreated(event.get('context'))

    def _onFrameAttached(self, frameId, parentFrameId):
        if self._frames.get(frameId):
            return
        assert parentFrameId
        parentFrame = self._frames.get(parentFrameId)
        frame = Frame(self.page, self._log, self._client, parentFrame, frameId)
        self._frames[frame._id] = frame

    def _onFrameNavigated(self, framePayload):
        isMainFrame = not framePayload.get('parentId')
        frame = self._mainFrame if isMainFrame else self._frames.get(framePayload.get('id'))

        assert isMainFrame or frame, 'We either navigate top level or have old version of the navigated frame'

        if frame:
            for child in frame.childFrames():
                self._removeFramesRecursively(child)
        if isMainFrame:
            if frame:
                self._frames.pop(frame._id)
                frame._id = framePayload.get('id')
            else:
                frame = Frame(self._page, self._log, self._client, None, framePayload.get(ID))

            self._frames[framePayload.get('id')] = frame
            self._mainFrame = frame
        frame._navigated(framePayload)

    def _onFrameDetached(self, frameId):
        frame = self._frames.get(frameId)
        if frame:
            self._removeFramesRecursively(frame)

    def _onExecutionContextCreated(self, contextPayload):

        contextid = contextPayload.get(ID)
        context = ExecutionContext(self._client, contextid, self.createJSHandle)
        self._contextIdToContext[contextid] = context

        frameId = contextPayload.get('auxData').get('frameId') if contextPayload.get('auxData') and contextPayload.get(
            'auxData').get('isDefault') else None
        frame = self._frames.get(frameId)
        if not frame:
            return
        frame._context = context
        for waitTask in frame._waitTasks:
            waitTask.rerun()

    def _onExecutionContextDestroyed(self, contextPayload):
        self._contextIdToContext.pop(contextPayload.get(ID))

    def _removeFramesRecursively(self, frame):
        if frame == None:
            return
        for child in frame.childFrames():
            self._removeFramesRecursively(child)
            frame._detach()
            self._frames.pop(frame._id)

    def isMainFrameLoadingFailed(self):
        return self._mainFrame._loadingFailed

    def createJSHandle(self, contextId, remoteObject):
        context = self._contextIdToContext.get(contextId)
        assert context, 'INTERNAL ERROR: missing context with id = ' + contextId

        if remoteObject and remoteObject.get('subtype') == 'node':
            return ElementHandle(context, self._client, remoteObject, self._page)
        return JSHandle(self._log, context, self._client, remoteObject, self._page)


class Frame():
    def __init__(self, page, log, client, parentFrame, frameId):
        self._page = page
        self._client = client
        self._log = log
        self._parentFrame = parentFrame
        self._url = ''
        self._id = frameId
        self._defaultContextId = '<not-initialized>'
        self._context = None
        self._waitTasks = set()

        self._childFrames = set()
        if self._parentFrame:
            self._parentFrame._childFrames.add(self)
        self._log.info('Frame created: frameid: {}'.format(frameId))

    def executionContext(self):
        return self._context

    async def evaluate(self, pageFunction, *args):
        return await self._context.evaluate(pageFunction, *args)

    async def S(self, selector):
        handle = await self._context.evaluateHandle(r'selector=> document.querySelector(selector)', selector)
        elementHanlder = handle.asElement()
        self._log.debug('elementHanlder was {}'.format(elementHanlder))
        if elementHanlder:
            return elementHanlder
        await elementHanlder.dispose()
        return None

    async def eval(self, selector, pageFunction, *args):
        elementHandle = await self.S(selector)
        if not elementHandle:
            raise RuntimeError('Error: failed to find element matching selector "{}"'.format(selector))

        result = await self.evaluate(pageFunction, elementHandle, *args)
        await elementHandle.dispose()
        return result

    async def SS(self, selector):
        arrayHandle = await self._context.evaluateHandle(r'selector => Array.from(document.querySelectorAll(selector))',
                                                         selector)

        properties = await arrayHandle.getProperties()
        await arrayHandle.dispose()

        result = []
        for property in properties.values():
            elementHandle = property.asElement()
            if elementHandle:
                result.push(elementHandle)
        return result

    async def Seval(self, selector, pageFunction, *args):
        arrayHandle = await  self._context.evaluateHandle(
            r'selector= > Array.from(document.querySelectorAll(selector))', selector)
        result = await self.evaluate(pageFunction, arrayHandle, *args)
        await arrayHandle.dispose()
        return result

    def name(self):
        return self._name if self._name else ''

    def url(self):
        return self._url

    def parentFrame(self):
        return self._parentFrame

    def childFrames(self):
        return self._childFrames

    def isDetached(self):
        return self._detached

    def _navigated(self, framePayload):
        self._name = framePayload.get('name')
        self._url = framePayload.get('url')
        self._loadingFailed = not not framePayload.get('unreachableUrl')
