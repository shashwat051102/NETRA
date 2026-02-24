from gtts import gTTS

import os

import time

from io import BytesIO

import base64

def text_to_speech(text, lang='en'):

    """Generate speech audio file WITHOUT opening it in media player.
    Returns the path to an mp3 file (legacy API for desktop app).
    """

    timestamp = str(int(time.time() * 1000))

    filename = f'output_{timestamp}.mp3'

    tts = gTTS(text=text, lang=lang)

    tts.save(filename)

    return filename

def text_to_speech_b64(text, lang='en'):

    """Generate speech as base64 mp3 without touching disk (faster, no I/O).

    Returns:
        str: Base64-encoded mp3 data suitable for data: URLs or transport.
    """

    tts = gTTS(text=text, lang=lang)

    buf = BytesIO()

    tts.write_to_fp(buf)

    buf.seek(0)

    return base64.b64encode(buf.read()).decode('utf-8')
