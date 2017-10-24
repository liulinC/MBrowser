# -*- coding: utf-8 -*-

import logging
import os

from MBrowser import helper
from MBrowser.Const import *
from MBrowser.ExecutionContext import ExecutionContext, JSHandle
from MBrowser.Session import Session

__all__ = ['ElementHandle']


class ElementHandle(JSHandle):
    def __init__(self, context: ExecutionContext, client: Session, remoteObject: dict, page: object):
        self._log = logging.getLogger('ElementHandle.ElementHandle')
        self._context = context
        self._client = client
        self._remoteObject = remoteObject
        self._page = page
        self._disposed = False

    def asElement(self):
        return self

    async def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        await helper.releaseObject(self._client, self._remoteObject)

    async def _visibleCenter(self):
        await self._scrollIntoViewIfNeeded()
        box = await self.boundingBox()
        return {
            'x': box.get('x') + box.get('width') / 2,
            'y': box.get('y') + box.get('height') / 2
        }

    async def hover(self):
        result = await self._visibleCenter()
        if result:
            await self._page.mouse.move(result.get('x'), result.get('y'))

    def _remoteObjectId(self):
        return self._remoteObject.get('objectId') if self._remoteObject and self._remoteObject.get('objectId') else None

    async def hover(self):
        (x, y) = await self._visibleCenter()
        await self._mouse.move(x, y)

    async def click(self, options: dict):
        result = await self._visibleCenter()
        if result:
            return await self._page._mouse.click(result.get('x'), result.get('y'), options)

    async def uploadFile(self, *filePaths: str):
        files = [os.path.resolve(filepath) for filepath in filePaths]
        objectId = self._remoteObject.get('objectId')
        return self._client.send('DOM.setFileInputFiles', dict(objectId=objectId, files=files))

    async def tap(self):
        result = await self._visibleCenter()
        if result:
            return await self._page._touchscreen.tap(result.get('x'), result.get('y'))

    async def focus(self):
        await self.executionContext().evaluate(r'element= > element.focus()', self)

    async def _scrollIntoViewIfNeeded(self):
        error = await self.executionContext().evaluate(r"""element => {
            if (!element.ownerDocument.contains(element))
                return 'Node is detached from document';
            if (element.nodeType !== Node.ELEMENT_NODE)
                return 'Node is not of type HTMLElement';
            element.scrollIntoViewIfNeeded();
            return false;
            }""", self)
        if error:
            raise RuntimeError("ERROR when run _scrollIntoViewIfNeeded")

    async def boundingBox(self):
        model = await self._client.send('DOM.getBoxModel', dict(
            objectId=self._remoteObject.get(OBID)
        ))
        if not model:
            raise RuntimeError('Node is detached from document')

        quad = model.get(RESULT).get('model').get('border')
        x = min(quad[0], quad[2], quad[4], quad[6])
        y = min(quad[1], quad[3], quad[5], quad[7])
        width = max(quad[0], quad[2], quad[4], quad[6]) - x
        height = max(quad[1], quad[3], quad[5], quad[7]) - y

        return {'x': x, 'y': y, 'width': width, 'height': height}

    async def type(self, text: str, options: dict = {}):
        await self.focus()
        await self._page.keyboard.type(text, options)

    async def press(self, key: str, options: dict = {}):
        await self.focus()
        await self._page.keyboard.press(key, options)

    async def screenshot(self, options: dict = {}):
        await self._scrollIntoViewIfNeeded()
        boundingBox = await self.boundingBox()
        options.update({'clip': boundingBox})
        return await self._page.screenshot(options)
