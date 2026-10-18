import threading
import time
import warnings
from unittest.mock import Mock

import numpy as np
import pytest
import loopback


INFO = {'speaker_id': 'test-output', 'max_input_channels': 2, 'default_samplerate': 48000}


def test_loopback_captures_and_closes_on_worker_thread(monkeypatch):
    data = np.array([[0.25, -0.25]], dtype=np.float32)
    context = Mock()
    def record(**kwargs):
        time.sleep(0.005)
        return data
    context.__enter__ = Mock(return_value=Mock(record=record))
    context.__exit__ = Mock(return_value=False)
    backend = Mock()
    backend.get_microphone.return_value.recorder.return_value = context
    monkeypatch.setattr(loopback, 'soundcard', backend)
    uninitialize = Mock()
    monkeypatch.setattr(loopback, 'initialize_com', lambda: uninitialize)
    ready = threading.Event()
    chunks = []
    def callback(samples, *args):
        chunks.append(samples.copy())
        ready.set()
    stream = loopback.LoopbackStream(INFO, callback)
    stream.start()
    assert ready.wait(1)
    stream.stop()
    stream.close()
    np.testing.assert_array_equal(chunks[0], data)
    backend.get_microphone.assert_called_once_with('test-output', include_loopback=True)
    backend.get_microphone.return_value.recorder.assert_called_once_with(
        samplerate=48000, channels=2, blocksize=9600)
    assert not stream._thread.is_alive()
    assert stream.error is None
    context.__exit__.assert_called_once()
    uninitialize.assert_called_once()


def test_loopback_discontinuity_reaches_recording_status(monkeypatch):
    ready = threading.Event()
    statuses = []
    def record(**kwargs):
        warnings.warn('data discontinuity', RuntimeWarning)
        time.sleep(0.005)
        return np.ones((3, 2), dtype=np.float32)
    context = Mock()
    context.__enter__ = Mock(return_value=Mock(record=record))
    context.__exit__ = Mock(return_value=False)
    backend = Mock(SoundcardRuntimeWarning=RuntimeWarning)
    backend.get_microphone.return_value.recorder.return_value = context
    monkeypatch.setattr(loopback, 'soundcard', backend)
    monkeypatch.setattr(loopback, 'initialize_com', lambda: lambda: None)
    def callback(data, frames, timestamp, status):
        statuses.append(status)
        ready.set()
    stream = loopback.LoopbackStream(INFO, callback)
    stream.start()
    assert ready.wait(1)
    stream.stop()
    assert 'WASAPI data discontinuity' in statuses


def test_loopback_start_failure_propagates_and_cleans_up(monkeypatch):
    backend = Mock()
    backend.get_microphone.side_effect = RuntimeError('device removed')
    monkeypatch.setattr(loopback, 'soundcard', backend)
    uninitialize = Mock()
    monkeypatch.setattr(loopback, 'initialize_com', lambda: uninitialize)
    stream = loopback.LoopbackStream(INFO, Mock())
    with pytest.raises(RuntimeError, match='device removed'):
        stream.start()
    stream.close()
    assert not stream._thread.is_alive()
    uninitialize.assert_called_once()
