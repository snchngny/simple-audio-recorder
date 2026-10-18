"""Windowsの既定再生デバイスをWASAPIループバックで録音する。"""
import ctypes
import sys
import threading

if sys.platform == 'win32':
    import soundcard
else:
    soundcard = None

LOOPBACK_DEVICE = -2


def loopback_info():
    if soundcard is None:
        raise RuntimeError('PC再生音の録音はWindowsで利用できます')
    speaker = soundcard.default_speaker()
    if speaker is None:
        raise RuntimeError('既定の再生デバイスがありません')
    return {'name': f'PC再生音: {speaker.name}',
            'max_input_channels': speaker.channels,
            'default_samplerate': 48000,
            'speaker_id': speaker.id}


def initialize_com():
    ole32 = ctypes.OleDLL('ole32')
    result = ole32.CoInitializeEx(None, 0)
    if result not in (0, 1):
        raise RuntimeError(f'音声スレッドの初期化に失敗しました: {result}')
    return ole32.CoUninitialize


class LoopbackStream:
    def __init__(self, device_info, callback):
        self.info = device_info
        self.callback = callback
        self.error = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        if not self._ready.wait(5):
            self._stop.set()
            raise RuntimeError('PC再生音の録音開始がタイムアウトしました')
        if self.error is not None:
            raise self.error

    def _run(self):
        uninitialize = None
        try:
            uninitialize = initialize_com()
            source = soundcard.get_microphone(self.info['speaker_id'], include_loopback=True)
            rate = self.info['default_samplerate']
            with source.recorder(samplerate=rate, channels=self.info['max_input_channels']) as recorder:
                self._ready.set()
                while not self._stop.is_set():
                    data = recorder.record(numframes=rate // 10)
                    self.callback(data, len(data), None, None)
        except Exception as error:
            self.error = error
        finally:
            self._ready.set()
            if uninitialize is not None:
                uninitialize()

    def stop(self):
        self._stop.set()
        if self._thread.ident is not None:
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                raise RuntimeError('PC再生音の録音を停止できませんでした')

    def close(self):
        self.stop()
