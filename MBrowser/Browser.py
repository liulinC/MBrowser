# -*- coding: utf-8 -*-

import logging

from MBrowser.Connections import Connection
from MBrowser.Const import *
from MBrowser.Pages import Page

__all__ = ['Browser']


class Browser(object):
    def __init__(self, browserWSEndpoint: str = ''):
        self._log = logging.getLogger('Browser.Browser')
        self._ws_url = browserWSEndpoint
        self._isconnected = False
        self._connection = None
        self._pages = []

    async def connect(self) -> Connection:
        if not self._isconnected:
            self._connection = await Connection.create(self._ws_url)
            self._isconnected = True
            return self._connection

    async def createPage(self) -> Page:
        if self._isconnected:
            result = await self._connection.send("Target.createTarget", dict(url='about:blank'))
            session = await self._connection.createSession(result.get(TID))
            page = Page(session)
            self._log.info('Page created for session {}'.format(session))
            self._pages.append(page)

            return page
