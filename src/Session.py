# -*- coding: utf-8 -*-

import asyncio
import json
import logging

from . import EventLoop
from .Const import *
from .EventEmitter import EventEmitter


class Session(EventEmitter):
    def __init__(self, connection, targetId: str, sessionId: str):
        self._log = logging.getLogger('Browser.Session')
        self._connection = connection
        self._targetId = targetId
        self._sessionId = sessionId
        self._msgid = 0
        self._sessionAcks = {}
        self.on(SE, self.send)

    def __msgid(self):
        self._msgid = self._msgid + 1
        return self._msgid

    def _onMessage(self, msg: str):
        event = json.loads(msg)
        if event.get(METHOD):
            self._log.debug('◀ RECV Event: {} '.format(event.get(METHOD)))
            self.emit(event.get(METHOD), event.get(METHOD), event.get(PARAMS))
            return
        if event.get(ID):
            self._log.debug('◀ RECV ACK with msgid: {}'.format(event.get(ID)))
            fat = self._sessionAcks.get(event.get(ID))
            if event.get(ERROR):
                self._log.error('Session get Error Response: {}'.format(event))
            if fat:
                self._sessionAcks.pop(event.get(ID))
                fat.set_result(event)
            else:
                self._log.warning('Not found ackcallback {}'.format(event))
            return

    def _onClosed(self):
        pass

    async def send(self, method: str, params: dict = None) -> object:
        msgid = self.__msgid()

        command = json.dumps(dict(id=msgid, method=method, params=params))
        try:
            if command and self._connection:
                fat = EventLoop.create_future()
                self._sessionAcks[msgid] = fat
                await self._connection.send('Target.sendMessageToTarget',
                                            dict(sessionId=self._sessionId, message=command))
                self._log.info('SEND ▶  msgid: {} msg: {}'.format(msgid, command))
                return await asyncio.wait_for(fat, TIMEOUT_S)
            else:
                self._log.error('command {} and connection {} error'.format(command, self._connection))
        except TimeoutError as e:
            self._log.error('time out for msgid: {} method: {}'.format(msgid, method))
            self._sessionAcks.pop(msgid)
        return None
