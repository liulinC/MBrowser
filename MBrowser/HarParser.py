# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import re
import urllib
from datetime import datetime

from MBrowser.Const import *
from MBrowser.EventEmitter import EventEmitter


class harinfo(object):
    def __init__(self):
        self._url = ''
        self._user = ''
        self._firstRequestId = None
        self._firstRequestMs = None
        self._domContentEventFiredMs = None
        self._loadEventFiredMs = None
        self._entries = {}
        pass

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = url

    @property
    def user(self):
        return self._user

    @url.setter
    def user(self, user):
        self._user = user

    @property
    def firstRequestId(self):
        return self._firstRequestId

    @firstRequestId.setter
    def firstRequestId(self, firstRequestId):
        self._firstRequestId = firstRequestId

    @property
    def firstRequestMs(self):
        return self._firstRequestMs

    @firstRequestMs.setter
    def firstRequestMs(self, firstRequestMs):
        self._firstRequestMs = firstRequestMs

    @property
    def domContentEventFiredMs(self):
        return self._domContentEventFiredMs

    @domContentEventFiredMs.setter
    def domContentEventFiredMs(self, domContentEventFiredMs):
        self._domContentEventFiredMs = domContentEventFiredMs

    @property
    def loadEventFiredMs(self):
        return self._loadEventFiredMs

    @loadEventFiredMs.setter
    def loadEventFiredMs(self, loadEventFiredMs):
        self._loadEventFiredMs = loadEventFiredMs

    @property
    def entries(self):
        return self._entries

    @entries.setter
    def entries(self, entries):
        self._entries = entries


class HarHandler(EventEmitter):
    def __init__(self):
        self._harinfo = harinfo()
        self._stopMsg = False
        self._log = logging.getLogger('HarHandler.HarHandler')
        self._client = None
        self._events = [Network_loadingFinished,
                        Page_domContentEventFired,
                        Page_loadEventFired,
                        Network_requestWillBeSent,
                        Network_dataReceived,
                        Network_responseReceived,
                        Network_resourceChangedPriority,
                        Security_securityStateChanged,
                        Network_loadingFailed]
        pass

    async def getHar(self, filehandler):
        if self._client == None:
            return None
        await self._checkFinsh()
        har = await HarParser().getHAR(self._harinfo)
        json.dump(har, filehandler, indent=4)

    def start(self, client):
        self._client = client
        self.on(self._events, self._processEvents)

    def stop(self):
        if self._client == None:
            self._client.removeAllEvents(self._events)

    async def _processEvents(self, *arg, **kargs):
        if self._harinfo != None and not self._stopMsg:
            (event_name, event) = arg

            if event_name == Page_domContentEventFired:
                self._harinfo.domContentEventFiredMs = event.get('timestamp') * 1000
                return
            if event_name == Page_loadEventFired:
                self._harinfo.loadEventFiredMs = event.get('timestamp') * 1000
                return
            if event_name == Network_requestWillBeSent:

                requestId = event.get(RID)
                initiator = event.get('initiator')
                timestamp = event.get('timestamp')
                redirectResponse = event.get('redirectResponse')

                if event.get('request').get('url').startswith('data'):
                    return
                if self._harinfo.entries.get(requestId) != None:
                    return
                if not self._harinfo.firstRequestId and initiator.get('type') == 'other':
                    self._harinfo.firstRequestId = requestId
                    self._harinfo.firstRequestMs = timestamp * 1000

                if redirectResponse:
                    redirectEntry = self._harinfo.entries.get(requestId)
                    if not redirectEntry:
                        redirectEntry = {}
                    redirectEntry['responseParams'] = {'response': redirectResponse}
                    redirectEntry['responseFinishedS'] = timestamp
                    redirectEntry['encodedResponseLength'] = redirectResponse.encodedDataLength
                    newId = str(requestId) + '_redirect_' + str(timestamp)
                    self._harinfo.entries[newId] = redirectEntry

                self._log.debug('new entry with id {}'.format(requestId))

                self._harinfo.entries[requestId] = {
                    REQPARAM: event,
                    RESPPRAM: None,
                    'responseLength': 0,
                    'encodedResponseLength': None,
                    'responseFinishedS': None,
                    'responseBody': '',
                    'responseBodyIsBase64': None,
                    'newPriority': None
                }

                return
            if event_name == Network_dataReceived:
                entry = self._harinfo.entries.get(event.get(RID))
                if not entry:
                    return
                entry['responseLength'] = entry.get('responseLength') + int(event.get('dataLength'))
            if event_name == Network_responseReceived:
                entry = self._harinfo.entries.get(event.get(RID))
                if not entry:
                    return
                entry[RESPPRAM] = event
            if event_name == Network_resourceChangedPriority:
                entry = self._harinfo.entries.get(event.get(RID))
                if not entry:
                    return
                entry['newPriority'] = event.get('newPriority')
            if event_name == Network_loadingFailed:
                entry = self._harinfo.entries.get(event.get(RID))
                if not entry:
                    return
                self._log.error(
                    'load failed for entry {} errorText: {} canceled:{} blockedReason:{}'.format(event.get(RID),
                                                                                                 event.get('errorText'),
                                                                                                 event.get('canceled'),
                                                                                                 event.get(
                                                                                                     'blockedReason')))
                self._harinfo.entries.pop(event.get(RID))
            if event_name == Network_loadingFinished:
                self._log.debug('get FinishedEvent entry {}'.format(event.get(RID)))
                entry = self._harinfo.entries.get(event.get(RID))
                if not entry:
                    return
                entry['encodedResponseLength'] = event.get('encodedDataLength')
                entry['responseFinishedS'] = event.get('timestamp')

                url = entry.get(REQPARAM).get('request').get('url')

                result = await self._client.send('Network.getResponseBody', dict(requestId=event.get(RID)))
                if result:
                    if result.get('result') and result.get('result').get('cookies'):
                        cookies = result.get('result').get('cookies')
                        if cookies:
                            entry['cookies'] = cookies
                            return
                    if result.get('result') and result.get('result').get('body'):
                        body = result.get('result').get('body')
                        if body:
                            entry['responseBody'] = body
                            entry['responseBodyIsBase64'] = result.get('result').get('base64Encoded')
                            return
                        else:
                            entry['responseBody'] = ''
                            return
                else:
                    self._log.error('Error: result was: {}'.format(result))
            if event_name == Security_securityStateChanged:
                if event.get('securityState') == 'secure' and len(event.get('explanations')) > 0:
                    for cer in [ex.get('certificate') for ex in event.get('explanations') if ex.get('certificate')]:
                        self._log.debug('get cer {}'.format(cer))

        pass

    async def _checkFinsh(self):
        while True:
            if self._harinfo.firstRequestMs and self._harinfo.domContentEventFiredMs and self._harinfo.loadEventFiredMs:
                break
            else:
                await asyncio.sleep(0.3)


class HarParser(object):
    def __init__(self):
        self._log = logging.getLogger('HarParser.HarParser')
        self._timeformat = '%Y-%m-%dT%H:%M:%S.%fZ'
        pass

    async def getHAR(self, harinfo):
        har = {
            'log': {
                'version': '1.2',
                'creator': {
                    'name': 'Chrome HAR Capturer',
                    'version': '537.36'
                },
                'pages': [],
                'entries': []
            }
        }
        pageId = 'page_1'
        result = self.parsePage(pageId, harinfo)
        har['log']['pages'].append(result['pages'])
        har['log']['entries'] = result['entries']

        return har

    def parsePage(self, pageid, page):
        firstRequest = page.entries.get(page.firstRequestId).get(REQPARAM)
        wallTimeMs = firstRequest.get('wallTime')

        startedDateTime = datetime.fromtimestamp(wallTimeMs).strftime(self._timeformat)

        onContentLoad = int(page.domContentEventFiredMs) - int(page.firstRequestMs)
        onLoad = int(page.loadEventFiredMs) - int(page.firstRequestMs)

        entries = []
        for ereqid, entry in page.entries.items():
            result = self.parseEntry(ereqid, pageid, entry)
            if result == None:
                self._log.error('parseEntry failed for {} None'.format(ereqid))
                continue
            entries.append(result)
        return dict(
            pages=dict(
                id=pageid,
                title=page.url,
                startedDateTime=startedDateTime,
                pageTimings=dict(
                    onContentLoad=onContentLoad,
                    onLoad=onLoad)),
            entries=entries
        )

    def parseEntry(self, ereqid, pageref, entry):
        # skip requests without response (requestParams is always present)
        if not entry.get(RESPPRAM) or not entry.get('responseFinishedS'):
            return None
        # skip entries without timing information (doc says optional)
        if not entry.get(RESPPRAM).get('response').get('timing'):
            return None

        # // extract common fields
        reqParams = entry.get(REQPARAM)
        resParams = entry.get(RESPPRAM)

        request = reqParams.get('request')
        response = resParams.get('response')
        # entry started
        wallTimeMs = reqParams.get('wallTime')

        startedDateTime = datetime.fromtimestamp(wallTimeMs).strftime(self._timeformat)

        httpVersion = response.get('protocol') if response.get('protocol') else ' '

        method = request.get('method')
        url = request.get('url')
        status = response.get('status')
        statusText = response.get('statusText')

        # // parse and measure headers
        headers = self.parseHeaders(httpVersion, request, response)

        # self._log.info('header is {}'.format(headers))

        # // check for redirections
        redirectURL = self.getHeaderValue(response.get('headers'), 'location', '')
        queryString = self.parseQueryString(request.get('url'))
        (times, timings) = self.computeTimings(entry)

        serverIPAddress = response.get('remoteIPAddress')

        connection = str(response.get('connectionId'))
        initiator = reqParams.get('initiator')
        changedPriority = entry.get('changedPriority')
        newPriority = changedPriority and changedPriority.get('newPriority')
        _priority = newPriority or request.get('initialPriority')

        payload = self.computePayload(entry, headers)

        mimeType = response.get('mimeType')

        encoding = 'base64' if response.get('responseBodyIsBase64') else ''

        scookies = entry.get('cookies') if entry.get('cookies') else []

        return {
            'pageref': pageref,
            'startedDateTime': startedDateTime,
            'time': times,
            'request': {
                'method': method,
                'url': url,
                'httpVersion': httpVersion,
                'cookies': scookies,
                'headers': headers.get('request').get('pairs'),
                'queryString': queryString,
                'headersSize': headers.get('request').get('size'),
                'bodySize': payload.get('request').get('bodySize')
            },
            'response': {
                'status': status,
                'statusText': statusText,
                'httpVersion': httpVersion,
                'cookies': [],
                'headers': headers.get('response').get('pairs'),
                'redirectURL': redirectURL,
                'headersSize': headers.get('response').get('size'),
                'bodySize': payload.get('response').get('bodySize'),
                '_transferSize': payload.get('response').get('transferSize'),
                'content': {
                    'size': entry.get('responseLength'),
                    'mimeType': mimeType,
                    'compression': payload.get('response').get('compression'),
                    'text': entry.get('responseBody')
                }
            },
            'cache': {},
            'timings': timings,
            'serverIPAddress': serverIPAddress,
            'connection': connection,
            'initiator': initiator,
            'priority': _priority,
        }

    def parseHeaders(self, httpVersion, request, response):
        requestHeaders = response.get('requestHeaders') if response.get('requestHeaders') else request.get('headers')
        responseHeaders = response.get('headers')
        headers = {
            'request': {
                'map': requestHeaders,
                'pairs': self.zipNameValue(requestHeaders),
                'size': -1
            },
            'response': {
                'map': responseHeaders,
                'pairs': self.zipNameValue(responseHeaders),
                'size': -1
            }
        }
        if httpVersion.startswith('http/'):
            requestText = self.getRawRequest(request, headers.get('request').get('pairs'))
            responseText = response.get('headersText') if response.get('headersText') else self.getRawResponse(response,
                                                                                                               headers.get(
                                                                                                                   'response').get(
                                                                                                                   'pairs'))
            headers['request']['size'] = len(requestText)
            headers['response']['size'] = len(responseText)

        return headers

    def computeTimings(self, entry):
        timing = entry.get(RESPPRAM).get('response').get('timing')
        if timing == None:
            return (0,
                    {'blocked': -1, 'dns': -1, 'connect': -1, 'send': -1, 'wait': -1, 'receive': -1, 'ssl': -1})
        times = self.toMilliseconds(entry.get('responseFinishedS') - timing.get('requestTime'))

        dnsStart = timing.get('dnsStart')
        sendStart = timing.get('sendStart')
        connectStart = timing.get('connectStart')
        sendEnd = timing.get('sendEnd')
        receiveHeadersEnd = timing.get('receiveHeadersEnd')
        sslStart = timing.get('sslStart')
        sslEnd = timing.get('sslEnd')
        blocked = self.firstNonNegative([
            dnsStart, connectStart, sendStart
        ])
        dns = -1
        if dnsStart >= 0:
            start = self.firstNonNegative([connectStart, sendStart])
            dns = start - dnsStart
        connect = -1
        if connectStart >= 0:
            connect = sendStart - connectStart

        send = sendEnd - sendStart
        wait = receiveHeadersEnd - sendEnd
        receive = times - receiveHeadersEnd
        ssl = -1
        if sslStart >= 0 and sslEnd >= 0:
            ssl = sslEnd - sslStart

        return (times,
                dict(blocked=blocked, dns=dns, connect=connect, send=send, wait=wait, receive=receive,
                     ssl=ssl))

    def computePayload(self, entry, headers):
        bodySize = 0
        compression = ''
        transferSize = entry.get('encodedResponseLength')
        respsize = headers.get('response').get('size')
        if respsize == -1:
            bodySize = -1
            compression = ''
        else:
            bodySize = entry.get('encodedResponseLength') - respsize
            compression = entry.get('responseLength') - bodySize

        return dict(
            request=dict(
                bodySize=int(self.getHeaderValue(headers.get('request').get('map'), 'content-length', -1))
            ),
            response=dict(
                bodySize=bodySize,
                transferSize=transferSize,
                compression=compression)
        )

    def zipNameValue(self, headers):
        pairs = []
        for k, v in headers.items():
            values = v if type(v) is list else [v]
            for v1 in values:
                pairs.append({'name': k, 'value': v1})
        return pairs

    def getRawRequest(self, request, headerPairs):
        method = request.get('request')
        url = request.get('url')
        protocol = request.get('protocol')

        lines = '{} {} {},'.format(method, url, protocol)
        for kv in headerPairs:
            for k, v in kv.items():
                lines = lines + '{}:{},'.format(k, v)
        lines += ','
        return lines

    def getRawResponse(self, response, headerPairs):
        status = response.get('status')
        statusText = response.get('statusText')
        protocol = response.get('protocol')

        lines = '{} {} {},'.format(protocol, status, statusText)
        for kv in headerPairs:
            for k, v in kv.items():
                lines = lines + '{}:{},'.format(k, v)
        lines += ','
        return lines

    def getHeaderValue(self, headers, name, fallback):
        pattern = re.compile(r'^{}$'.format(name), re.I)
        result = [key for key in headers.keys() if pattern.match(key)]
        if len(result) == 0:
            return fallback
        return headers[result[0]]

    def parseQueryString(self, requestUrl):
        query = urllib.parse.urlparse(requestUrl)
        result = urllib.parse.parse_qs(query.query)
        return self.zipNameValue(result)

    def firstNonNegative(self, values):
        value = [value for value in values if value > 0]
        return value[0]

    def toMilliseconds(self, time):
        return time * 1000 if not time == -1 else -1
