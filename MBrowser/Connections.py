# -*- coding: utf-8 -*-


import asyncio
import json
import logging

import websockets
import websockets.protocol

from . import EventLoop
from .Const import *
from .Session import Session

__all__ = ['Connection']


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Connection(metaclass=Singleton):
    mid = 0

    def __init__(self, ws: str):
        self._ws = ws
        self._sessions = {}
        self._connected = False
        self._msgQ = {}
        self._log = logging.getLogger('Connections.Connection')
        self._send_log = logging.getLogger('Connections.Connection.send_handler')
        self._recv_log = logging.getLogger('Connections.Connection.recv_handler')
        self._recv_task = None
        self._createReceiveTask()
        self._stopping = False
        self._log.info('Connection init done')

    @staticmethod
    async def create(ws_url: str):
        """
        Create a websocket connection to Browser
        :param ws_url: String
        :return: Connection
        """
        ws = await websockets.connect(ws_url, max_size=MAX_PAYLOAD_SIZE_BYTES)
        logging.getLogger('Connections.Connection').info('WS connected: {}'.format(ws_url))
        connection = Connection(ws)
        connection._connected = True
        return connection

    def _createReceiveTask(self):
        self._recv_task = EventLoop.create_task(self.receive())
        return self._recv_task

    def _msgid(self) -> int:
        self.mid = self.mid + 1
        return self.mid

    def close(self):
        self._stopping = True
        self._sessions.clear()
        self._ws.close()
        self._connected = False
        if self._recv_task != None:
            self._recv_task.cancel()

    async def receive(self):
        try:
            while True:
                if self._stopping:
                    break
                result = await self._ws.recv()
                self._recv_log.debug('◀ RECV {}'.format(result))
                if not result:
                    self._recv_log.error('Missing message, may have been a connection timeout...')
                    continue
                result = json.loads(result)
                if not isinstance(result, dict):
                    self._recv_log.error('decoded messages is of type "%s" and = "%s"' % (type(result), result))
                    continue
                if ID in result:
                    #### ack msg
                    msgid = result[ID]
                    # self._recv_log.info('Received ACK message id = {}!'.format(msgid))
                    future = self._msgQ.get(msgid)
                    if result.get(ERROR):
                        self._recv_log.error('get Error Response: {}'.format(result))
                    if future:
                        future.set_result(result.get(RESULT))
                        self._msgQ.pop(msgid)
                    else:
                        self._recv_log.error('Not found valid msg request with id {}'.format(msgid))
                    continue
                elif METHOD in result:
                    #### Event
                    event = result.get(PARAMS)
                    event_name = result.get(METHOD)
                    if event_name == 'Target.receivedMessageFromTarget':
                        sessionId = event.get(SID)
                        session = self._sessions.get(sessionId)
                        if session:
                            session._onMessage(event.get(MSG))
                        else:
                            self._recv_log.warn('get a valid event sid {}'.format(sessionId))
                    elif event_name == 'Target.detachedFromTarget':
                        sessionId = event.get(SID)
                        session = self._sessions.get(sessionId)
                        if session:
                            session._onClosed()
                            self._sessions.pop(sessionId)
                        else:
                            self._recv_log.warning('get a valid event sid {}'.format(sessionId))
                    else:
                        try:
                            sessionId = event.get(SID)
                        except:
                            self._recv_log.warning('unahndle event msg {}'.format(event))
                            continue
        except asyncio.TimeoutError:
            raise TimeoutError('Unknown cause for timeout to occurs')
        except Exception as e:
            self._recv_log.exception(e)
            if self._ws.state != websockets.protocol.OPEN:
                raise ConnectionError('Websocket lost with {} code'.format(self._ws.close_code))

    async def send(self, method: str, param: dict = None, timeout: int = TIMEOUT_S) -> object:
        messageid = self._msgid()
        try:
            msg = json.dumps(dict(id=messageid, method=method, params=param))
            self._send_log.debug('SEND ► message id {} msg = {}'.format(messageid, msg))
            await self._ws.send(msg)
            future = EventLoop.create_future()
            self._msgQ[messageid] = future
            return await asyncio.wait_for(future, timeout)
        except Exception as e:
            self._send_log.exception(e)
            self._msgQ.pop(messageid)

    async def createSession(self, targetId: int) -> object:
        """
        Create a Session for a page
        :param targetId: String
        :return: session
        """
        sessionId = await self.send("Target.attachToTarget", dict(targetId=targetId))
        sessionId = sessionId[SID]
        session = Session(self, targetId, sessionId)
        self._sessions[sessionId] = session
        self._log.info('Session {} created'.format(sessionId))
        return session
