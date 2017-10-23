# -*- coding: utf-8 -*-
import logging
import re
from subprocess import Popen, PIPE, STDOUT

from .Browser import Browser
from .Const import BROWSEPATH

CHROMESTARTUPARGS = [
    r'--disable-background-networking',
    r'--disable-background-timer-throttling',
    r'--disable-client-side-phishing-detection',
    r'--disable-default-apps',
    r'--disable-hang-monitor',
    r'--disable-popup-blocking',
    r'--disable-prompt-on-repost',
    r'--disable-sync',
    r'--enable-automation',
    r'--enable-devtools-experiments',
    r'--metrics-recording-only',
    r'--no-first-run',
    r'--password-store=basic',
    r'--remote-debugging-port=0',
    r'--safebrowsing-disable-auto-update',
    r'--use-mock-keychain'
]
CHROMESHEADLESS = [
    r'--disable-hang-monitor',
    r'--disable-prompt-on-repost',
    r'--disable-gpu',
    r'--headless', ]


class Launcher(object):
    """
    Used to launch the chrome brower
    """
    browserPid = None

    @classmethod
    def startBrowser(cls, options):

        BROWSER = r'C:\APP\chrome32\chrome-win32\chrome.exe'

        cls._log = logging.getLogger('Launcher.Launcher')

        cls.killBrowser()
        if isinstance(options, dict) and options.get('headless') == True:
            CHROMESTARTUPARGS.extend(CHROMESHEADLESS)

        if isinstance(options, dict) and options.get(BROWSEPATH):
            BROWSER = options.get(BROWSEPATH)

        CHROMESTARTUPARGS.insert(0, BROWSER)

        # cls._log.info(CHROMESTARTUPARGS)
        browserWSEndpoint = ''
        cls._log.info('start paramters: {}'.format(CHROMESTARTUPARGS))
        cls.browserPid = Popen(CHROMESTARTUPARGS, stdout=PIPE, stderr=STDOUT)

        while cls.browserPid.poll() is None:
            line = cls.browserPid.stdout.readline()
            line = line.strip()
            if line:
                cls._log.info('Subprogram output: [{}]'.format(line))
                match = re.match(r'^DevTools listening on (ws:\/\/.*)$', line.decode('utf-8'))
                if match:
                    browserWSEndpoint = match.group(1)
                    break

        cls._log.info('browserWSEndpoint {}'.format(browserWSEndpoint))
        if (browserWSEndpoint == ''):
            return None

        browser = Browser(browserWSEndpoint=browserWSEndpoint)
        return browser

    @classmethod
    def killBrowser(cls):
        p1 = Popen(r'TASKLIST /FI "IMAGENAME eq chrome.exe"', stdin=PIPE, stdout=PIPE)
        p1.wait()
        pidlist = []
        for line in p1.stdout.readlines():
            line = str(line)
            if line.find(r'chrome') != -1:
                pidlist.append(line.split()[1])

        for pid in pidlist:
            p2 = Popen(r'TASKKILL /PID {} /F /T '.format(pid), stdin=PIPE, stdout=PIPE)
            p2.wait()
