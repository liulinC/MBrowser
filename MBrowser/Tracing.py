# -*- coding: utf-8 -*-

import logging


class Tracing(object):
    def __init(self, client):
        self._client = client
        self._recording = False
        self._path = ''
        self._log = logging.getLogger('Tracing.Tracing')

    async def start(self, options):
        if not self._recording:
            self._log.info('Cannot start recording trace while already recording trace.')
            return
        if not options.get('path'):
            self._log.info('Must specify a path to write trace file to.')
            return
        categoriesArray = ['-*', 'devtools.timeline', 'v8.execute', 'disabled-by-default-devtools.timeline',
                           'disabled-by-default-devtools.timeline.frame', 'toplevel',
                           'blink.console', 'blink.user_timing', 'latencyInfo',
                           'disabled-by-default-devtools.timeline.stack',
                           'disabled-by-default-v8.cpu_profiler']

        if options.screenshots:
            categoriesArray.append('disabled-by-default-devtools.screenshot')

        self._path = options.path
        self._recording = True
        await self._client.syncsend(
            'tracing.Tracing.start', dict(transferMode='ReturnAsStream', categories=categoriesArray.join(',')))

    async def stop(self):
        # contentPromise = new Promise(x => fulfill = x)                  #####
        # self._client.once('Tracing.tracingComplete', event => {
        #        self._readStream(event.stream, this._path).then(fulfill)})
        result = await self._client.send('tracing.Tracing.end', {})
        self._recording = False
        return result

    async def _readStream(self, handle, path):
        '''eof = False
        file = fs.openSync(path, 'w')
        while (not eof):
            response = await self._client.send('IO.read', {handle})
            eof = response.eof
            if path:
                fs.writeSync(file, response.data)
        fs.closeSync(file)
        await self._client.send('IO.close', {handle})'''
