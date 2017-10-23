# -*- coding: utf-8 -*-

import asyncio
import logging

__all__ = ['loop', 'execute']

loop = asyncio.get_event_loop()
log = logging.getLogger('Browser.EVENTLOOP')


def execute(cmd):
    result = None
    if not looprunning():
        result = loop.run_until_complete(cmd)
    else:
        result = create_task(cmd)
    return result


def looprunning():
    return loop.is_running()


def create_future():
    return loop.create_future()


def create_task(coro):
    return loop.create_task(coro)


def exceptionhandler(eloop, context):
    """
    Exception handle for event Loop

    :param eloop:
    :param context:
    :return:
    """
    try:
        message = context.get('message')
        if not message:
            message = 'Unhandled exception in event loop'

        exception = context.get('exception')
        if exception is not None:
            exc_info = (type(exception), exception, exception.__traceback__)
        else:
            exc_info = False

        if ('source_traceback' not in context
            and eloop._current_handle is not None
            and eloop._current_handle._source_traceback):
            context['handle_traceback'] = eloop._current_handle._source_traceback

        log_lines = [message]
        for key in sorted(context):
            if key in {'message', 'exception'}:
                continue
            value = context[key]
            if key == 'source_traceback':
                tb = ''.join(str(value))
                value = 'Object created at (most recent call last):\n'
                value += tb.rstrip()
            elif key == 'handle_traceback':
                tb = ''.join(str(value))
                value = 'Handle created at (most recent call last):\n'
                value += tb.rstrip()
            if type(value) is asyncio.Task:
                log.error('Task {} will be cancelled sine an exception happend'.format(id(value)))
                log_lines.append('{}: {}'.format(key, value._coro))
                value.cancel()
        log.error('\n'.join(log_lines), exc_info=exc_info)
    except Exception as e:
        log.exception(e)

# loop.set_exception_handler(exceptionhandler)
