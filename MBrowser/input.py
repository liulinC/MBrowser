# -*- coding: utf-8 -*-

import asyncio

from .Const import SE
from .EventEmitter import EventEmitter

__all__ = ['Keyboard', 'Mouse', 'Touchscreen']

class Keyboard(EventEmitter):
    def __init__(self, client, log):
        self._client = client
        self._log = log
        self._modifiers = 0
        self._pressedKeys = set()

    def _modifierBit(self, key):
        if key == 'Alt':
            return 1
        if key == 'Control':
            return 2
        if key == 'Meta':
            return 4
        if key == 'Shift':
            return 8
        return 0

    def down(self, key, option={}, **kwargs):
        options = option or dict()
        options.update(kwargs)
        text = options.get('text')
        self._pressedKeys.add(key)
        self._modifiers |= self._modifierBit(key)
        config = dict(
            type='rawKeyDown',
            modifiers=self._modifiers,
            windowsVirtualKeyCode=codeForKey(key),
            key=key,
        )
        if text:
            config['type'] = 'keyDown'
            config['text'] = text
            config['unmodifiedText'] = text
        if 'autoRepeat' in self._pressedKeys:
            config['autoRepeat'] = True

        self.emit(SE, 'Input.dispatchKeyEvent', config)

    def up(self, key):
        self._modifiers &= not self._modifierBit(key)
        self._pressedKeys.remove(key)
        self.emit(SE, 'Input.dispatchKeyEvent', dict(type='keyUp',
                                                     modifiers=self._modifiers,
                                                     windowsVirtualKeyCode=codeForKey(key),
                                                     key=key))

    def sendCharacter(self, char):
        self.emit(SE, 'Input.dispatchKeyEvent', dict(type='char',
                                                     modifiers=self._modifiers,
                                                     key=char,
                                                     text=char,
                                                     unmodifiedText=char))


class Mouse(EventEmitter):
    def __init__(self, client, keyboard, log):
        self._client = client
        self._log = log
        self._keyboard = keyboard
        self._x = 0
        self._y = 0
        self._button = 'none'

    def move(self, x, y, options={}):
        fromX = self._x
        fromY = self._y
        self._x = x
        self._y = y
        steps = options.get('steps') if options.get('steps') else 1
        self._button = options.get('button') if options and options.get('button') else 'none'
        for i in range(1, steps + 1):
            x = round(fromX + (self._x - fromX) * (i / steps))
            y = round(fromY + (self._y - fromY) * (i / steps))
            self.emit(SE, 'Input.dispatchMouseEvent', dict(type='mouseMoved',
                                                           button=self._button,
                                                           x=x,
                                                           y=y,
                                                           modifiers=self._keyboard._modifiers
                                                           ))

    async def click(self, x, y, options={}):
        self.move(x, y)
        await self.down(options)
        delay = options.get('delay') if options and options.get('delay') else 1
        if options and type(options.get('delay')) is type(10):
            await asyncio.sleep(delay)
        self.up(options)

    async def down(self, options={}):
        self._button = options.get('button') if options and options.get('button') else 'left'
        self.emit(SE, 'Input.dispatchMouseEvent', dict(type='mousePressed',
                                                       button=self._button,
                                                       x=self._x,
                                                       y=self._y,
                                                       modifiers=self._keyboard._modifiers,
                                                       clickCount=options.get(
                                                           'clickCount') if options and options.get(
                                                           'clickCount') else 1
                                                       ))

    def up(self, options={}):
        self.emit(SE, 'Input.dispatchMouseEvent', dict(type='mouseReleased',
                                                       button=options.get(
                                                           'button') if options and options.get(
                                                           'button') else 'left',
                                                       x=self._x,
                                                       y=self._y,
                                                       modifiers=self._keyboard._modifiers,
                                                       clickCount=options.get(
                                                           'clickCount') if options and options.get(
                                                           'clickCount') else 1
                                                       ))


class Touchscreen(EventEmitter):
    def __init__(self, client, keyboard, log):
        self._log = log
        self._client = client
        self._keyboard = keyboard

    async def tap(self, x, y):
        touchPoints = [{x: round(x), y: round(y)}]
        self.emit(SE, 'Input.dispatchTouchEvent', dict(type='touchStart',
                                                       touchPoints=touchPoints,
                                                       modifiers=self._keyboard._modifiers))
        self.emit(SE, 'Input.dispatchTouchEvent', dict(type='touchEnd',
                                                       touchPoints=[],
                                                       modifiers=self._keyboard._modifiers))


def codeForKey(key):
    if keys.get(key):
        return keys[key]
    if len(key) == 1:
        return ord(key.upper())
    return 0


keys = {
    'Cancel': 3,
    'Help': 6,
    'Backspace': 8,
    'Tab': 9,
    'Clear': 12,
    'Enter': 13,
    'Shift': 16,
    'Control': 17,
    'Alt': 18,
    'Pause': 19,
    'CapsLock': 20,
    'Escape': 27,
    'Convert': 28,
    'NonConvert': 29,
    'Accept': 30,
    'ModeChange': 31,
    'PageUp': 33,
    'PageDown': 34,
    'End': 35,
    'Home': 36,
    'ArrowLeft': 37,
    'ArrowUp': 38,
    'ArrowRight': 39,
    'ArrowDown': 40,
    'Select': 41,
    'Print': 42,
    'Execute': 43,
    'PrintScreen': 44,
    'Insert': 45,
    'Delete': 46,
    ')': 48,
    '!': 49,
    '@': 50,
    '#': 51,
    '$': 52,
    '%': 53,
    '^': 54,
    '&': 55,
    '*': 56,
    '(': 57,
    'Meta': 91,
    'ContextMenu': 93,
    'F1': 112,
    'F2': 113,
    'F3': 114,
    'F4': 115,
    'F5': 116,
    'F6': 117,
    'F7': 118,
    'F8': 119,
    'F9': 120,
    'F10': 121,
    'F11': 122,
    'F12': 123,
    'F13': 124,
    'F14': 125,
    'F15': 126,
    'F16': 127,
    'F17': 128,
    'F18': 129,
    'F19': 130,
    'F20': 131,
    'F21': 132,
    'F22': 133,
    'F23': 134,
    'F24': 135,
    'NumLock': 144,
    'ScrollLock': 145,
    'AudioVolumeMute': 173,
    'AudioVolumeDown': 174,
    'AudioVolumeUp': 175,
    'MediaTrackNext': 176,
    'MediaTrackPrevious': 177,
    'MediaStop': 178,
    'MediaPlayPause': 179,
    '': 186,
    ':': 186,
    '=': 187,
    '+': 187,
    ',': 188,
    '<': 188,
    '-': 189,
    '_': 189,
    '.': 190,
    '>': 190,
    '/': 191,
    '?': 191,
    '`': 192,
    '~': 192,
    '[': 219,
    '{': 219,
    '\\': 220,
    '|': 220,
    ']': 221,
    '}': 221,
    '\'': 222,
    '"': 222,
    'AltGraph': 225,
    'Attn': 246,
    'CrSel': 247,
    'ExSel': 248,
    'EraseEof': 249,
    'Play': 250,
    'ZoomOut': 251
}
