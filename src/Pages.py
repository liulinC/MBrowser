# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import Any

from . import helper
from .Const import *
from .EventEmitter import EventEmitter
from .FrameManager import Frame
from .FrameManager import FrameManager
from .HarParser import HarHandler
from .Session import Session
from .input import Keyboard, Mouse, Touchscreen


class Page(EventEmitter):
    def __init__(self, client: Session):
        self._client = client
        self._log = logging.getLogger('Page.Page')

        self._harhandler = None
        self._events = [Page_frameStartedLoading,
                        Page_frameStoppedLoading,
                        Network_loadingFailed,
                        Network_requestWillBeSent,
                        Runtime_executionContextCreated,
                        Runtime_executionContextDestroyed]
        self._startFrameId = None

        self._keyboard = Keyboard(self._client, self._log)
        self._mouse = Mouse(self._client, self._keyboard, self._log)
        self._touchscreen = Touchscreen(self._client, self._keyboard, self._log)
        self._frameManager = FrameManager(self._client, self)

        self._pageDone = False
        self._contextCreated = False
        self._enable()

    def _enable(self) -> None:
        self.emit(SE, 'Network.enable', {}),
        self.emit(SE, 'Security.enable', {}),
        self.emit(SE, 'Page.enable', {}),
        self.emit(SE, 'Runtime.enable', {})

    def _startHar(self) -> None:
        self._harhandler = HarHandler()
        self._harhandler.start(self._client)

    async def _processPageEvent(self, *arg: Any, **kargs: Any) -> None:
        (event_name, event) = arg
        if event_name == Page_frameStartedLoading:
            self._startFrameId = event.get('frameId')
            self._log.debug('get {} with frameID {} '.format(Page_frameStartedLoading, self._startFrameId))
            self._pageDone = False
            return
        if event_name == Page_frameStoppedLoading:
            if self._startFrameId == None:
                self._startFrameId = event.get('frameId')
            self._pageDone = True
            self._log.debug('get {} with frameID {} '.format(Page_frameStoppedLoading, event.get('frameId')))
            self._log.info('load page done')
            return
        if event_name == Network_loadingFailed:
            self._log.warning('page load failed: {}'.format(event))
            return
        if event_name == Runtime_executionContextCreated:
            self._contextCreated = True
            return
        if event_name == Runtime_executionContextDestroyed:
            self._contextCreated = False
            return
        if event_name == Network_requestWillBeSent:
            return

    async def waitForPageLoadFinish(self, timeout: int = TIMEOUT_S) -> None:
        breakFunction = lambda: self._pageDone == True
        await helper.waitFor(breakFunction, timeout)

    async def getHar(self, filename: str) -> None:
        self._log.info('Get har started')
        await asyncio.sleep(3)
        with open(filename, 'w') as fileHanlder:
            if self._harhandler != None:
                await self._harhandler.getHar(fileHanlder)
                self._harhandler.stop()
                self._log.info('Get Har done')
            else:
                self._log.error('Harhandler not started, so get har failed.')

    async def goto(self, url: str, transitionType: str = 'https', referrer: str = None, startHarRecord: bool = False,
                   waitFinish: bool = True) -> None:
        if startHarRecord:
            self._startHar()
        self._pageDone = False
        self.on(self._events, self._processPageEvent)

        if referrer == None:
            self.emit(SE, "Page.navigate", dict(url=url, transitionType=transitionType))
        else:
            self.emit(SE, "Page.navigate",
                      dict(url=url, transitionType=transitionType, referrer=referrer))
        if waitFinish:
            await self.waitForPageLoadFinish()

    async def types(self, text: str, options: dict = {}) -> None:
        delay = 0
        if options and options.get('delay'):
            delay = options.get('delay', 0)
        for char in text:
            await self.press(char, {'text': char, 'delay': delay})
            if delay:
                await asyncio.sleep(delay)

    async def type2(self, selector: str, text: str, options: dict = {}):
        handle = await self.S(selector)
        await handle.type(text, options)
        await handle.dispose()

    async def press(self, key: str, options: dict = {}, waitForLoadFinish: bool = False) -> None:
        self._pageDone = False
        self._keyboard.down(key, options)
        if options and options.get('delay'):
            await asyncio.sleep(options.get('delay'))
        self._keyboard.up(key)
        if waitForLoadFinish:
            await self.waitForPageLoadFinish()

    async def click(self, selector: str, options: dict = {}, waitForLoadFinish: bool = False) -> None:
        self._pageDone = False
        handle = await self.S(selector)
        assert handle, 'No node found for selector: ' + selector
        await handle.click(options)
        await handle.dispose()
        if waitForLoadFinish:
            await self.waitForPageLoadFinish()

    async def S(self, selector: str) -> object:
        return await self.mainFrame().S(selector)

    def mainFrame(self) -> Frame:
        return self._frameManager.mainFrame()

    async def tap(self, selector: str) -> None:
        handle = await self.S(selector)
        assert handle, 'No node found for selector: ' + selector
        await handle.tap()
        await handle.dispose()

    async def evaluate(self, pageFunction: str, *args: Any) -> Any:
        return await self._frameManager.mainFrame().evaluate(pageFunction, *args)

    async def evaluateHandle(self, pageFunction, *args):
        return self.mainFrame().executionContext().evaluateHandle(pageFunction, *args)

    async def queryObjects(self, prototypeHandle):
        return self.mainFrame().executionContext().queryObjects(prototypeHandle)

    def url(self):
        return self.mainFrame().url()

    async def evalateFromList(self, list_selector: str, itemDict: dict):
        """
        get item attubutes from a form of the page

        :param list_selector: selector to form of the page
        :param itemDict: dict, selector dict, {'key1':selectorValue, 'key2': selectorValue}
        :return: [{'key1': value, 'key2': value}]
        """
        return await self.evaluate(r'''(slist, optionsDict) => {
                return Array.prototype.slice.apply(document.querySelectorAll(slist))
                .map($itemoflist => {
        			const result = {};
        			for (var key in optionsDict) {
        				const $item = $itemoflist.querySelector(optionsDict[key]);
        				const temResult = $item ? $item.innerText : undefined;
        				result[key]=temResult;
        			}
        			return result;
                })}''', list_selector, itemDict)
