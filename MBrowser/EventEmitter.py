# -*- coding: utf-8 -*-

import logging
from asyncio import iscoroutine, ensure_future, Future, wait_for
from typing import Any

from MBrowser.Const import TIMEOUT_S

__all__ = ['EventEmitter']

_eventCallbacks = {}
_allEventCallback = []


class EventEmitter(object):
    def __init__(self):
        pass

    #################################### register ###############################
    def onAll(self, callback):
        """
        Register event listener(callback) to receive all Events
        :param callback: event listener, function to receive Events
        :return: None
        """
        _allEventCallback.append(callback)

    def onece(self, eventName: str, callback):
        """
        Register event listener(callback) to only receive event named eventName only once
        :param eventName: event name, string
        :param callback: event listener, function to receive event
        :return: None
        """
        self.on(eventName, callback, once=True)
        pass

    def on(self, events: list, callback, once: bool = False):
        """
        Register event listener(callback) to receive events
        :param events: list of event names
        :param callback: event listener, function to receive event
        :param once: once tag for receive event only, default False
        :return: None
        """
        if type(events) is list:
            for event in events:
                self.on(event, callback, once)
        else:
            callbacks = _eventCallbacks.get(events)
            if not callbacks:
                _eventCallbacks[events] = [(callback, once)]
            else:
                callbacks.append((callback, once))
            pass

    #################################### register ###############################

    #################################### remove #################################
    def removeEvent(self, eventName: str, callback=None):
        """
        Remove event listener(callback) for event(eventName)
        :param eventName: event name, string
        :param callback: event listener, function
        :return: None
        """
        if eventName == None and callback == None:
            return
        if eventName == None and callback != None and callback in _allEventCallback:
            _allEventCallback.pop(callback)
            return

        callbacks = _eventCallbacks.get(eventName)

        if callbacks and callback == None:
            _eventCallbacks.pop(eventName)
        if callbacks:
            for cb in [(cb, once) for cb, once in callbacks if cb == callback]:
                callbacks.pop(cb)
        pass

    def removeEvents(self, events: list):
        """
        Remove events(list) and related callbacks
        :param events: list of Event name
        :return: None
        """
        for event in events:
            self.removeEvent(event)

    #################################### remove #################################

    #################################### Emit ###################################
    def emit(self, eventName: str, *args: Any, waitRspAndReturn: bool = False, **kwargs: Any):
        """
        emit event.
        
        especially, the waitRspAndReturn, True means emit the event, and then get and result, and return directly
        it will only send to event listener, wait and get the result, don't emit to other event listener

        and if the waitRspAndReturn is True, the return of this function is a coroutine, you can await it to get the
        result, eg:
                result = await self.emit(EventName,param)

        if waitRspAndReturn is False, the emit will try to send the event to all relevant Event Listener


        :param eventName: event Name, string
        :param args:
        :param waitRspAndReturn: whether wait for response, default is False
        :param kwargs:
        :return: object, if waitRspAndReturn is True, the return would be a coroutine(_waitForResponse), you need to
                await it to get final result
        """
        for callback in _allEventCallback:
            result = callback(*args, **kwargs)
            if iscoroutine(result):
                futreult = ensure_future(result)
                if waitRspAndReturn:
                    return self._waitForResponse(futreult)
            else:
                if waitRspAndReturn:
                    return result

        callbacks = _eventCallbacks.get(eventName)
        if callbacks and len(callbacks) > 0:
            for cb in callbacks:
                (fun, once) = cb
                try:
                    result = fun(*args, **kwargs)
                    if iscoroutine(result):
                        futreult = ensure_future(result)
                        if waitRspAndReturn:
                            return self._waitForResponse(futreult)
                    else:
                        if waitRspAndReturn:
                            return result
                except TypeError as e:
                    logging.error('fun {} type Error: {}'.format(fun.__name__, e))
                except Exception as e:
                    logging.exception(e)
                if once:
                    callbacks.pop(cb)
                if len(callbacks) == 0:
                    _eventCallbacks.pop(eventName)
        else:
            logging.debug('no cb for event: {}'.format(eventName))
            # self._log.info('no cb for event: {} {}'.format(event.get(METHOD),event))
            #################################### Emit ###################################

    async def _waitForResponse(self, future: Future):
        return await wait_for(future, TIMEOUT_S)
