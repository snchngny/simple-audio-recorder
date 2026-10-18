import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('PYQTGRAPH_QT_LIB', 'PyQt6')

from unittest.mock import Mock
import numpy as np
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from scipy.io import wavfile
import main


@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def recorder(app, tmp_path, monkeypatch):
    window = main.AudioRecorder()
    window.settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    monkeypatch.setattr(main.sd, 'stop', Mock())
    monkeypatch.setattr(main.QMessageBox, 'critical', Mock())
    yield window
    window.close()


def mock_input(monkeypatch, channels=1):
    monkeypatch.setattr(main.sd, 'query_devices', lambda *args: {
        'name': 'Test input', 'max_input_channels': channels, 'default_samplerate': 48000,
    })
    monkeypatch.setattr(main.sd, 'check_input_settings', Mock())
    stream = Mock()
    constructor = Mock(return_value=stream)
    monkeypatch.setattr(main.sd, 'InputStream', constructor)
    return stream, constructor


def test_native_rate_and_mono_stereo_roundtrip(recorder, monkeypatch):
    stream, constructor = mock_input(monkeypatch)
    recorder.toggle_record()
    assert constructor.call_args.kwargs['samplerate'] == 48000
    assert constructor.call_args.kwargs['channels'] == 1
    assert not recorder.settings_btn.isEnabled()
    data = np.array([[0.1], [0.2], [-0.3]], dtype=np.float32)
    recorder.audio_callback(data, 3, None, None)
    recorder.toggle_record()
    np.testing.assert_array_equal(recorder.audio_data, np.repeat(data, 2, axis=1))
    stream.stop.assert_called_once()
    stream.close.assert_called_once()
    assert recorder.settings_btn.isEnabled()


def test_selected_channels(recorder, monkeypatch):
    mock_input(monkeypatch, channels=4)
    recorder.settings.setValue('audio_channel_l', 3)
    recorder.settings.setValue('audio_channel_r', 1)
    recorder.toggle_record()
    samples = np.array([[0.1, 0.2, 0.3, 0.4]], dtype=np.float32)
    recorder.audio_callback(samples, 1, None, None)
    recorder.toggle_record()
    np.testing.assert_array_equal(recorder.audio_data, samples[:, [3, 1]])


def test_failed_start_closes_stream(recorder, monkeypatch):
    stream, _ = mock_input(monkeypatch)
    stream.start.side_effect = RuntimeError('device unavailable')
    recorder.toggle_record()
    assert not recorder.is_recording
    assert recorder.stream is None
    stream.close.assert_called_once()
    main.QMessageBox.critical.assert_called_once()


def test_close_releases_active_input(recorder, monkeypatch):
    stream, _ = mock_input(monkeypatch)
    recorder.toggle_record()
    recorder.close()
    stream.stop.assert_called_once()
    stream.close.assert_called_once()


def test_trim_speed_and_pcm_export(recorder, monkeypatch, tmp_path):
    recorder.audio_data = np.array([[0, 0], [2, -2], [0.5, -0.5], [0, 0]], dtype=np.float32)
    recorder.sample_rate = 48000
    recorder.trim_end_line.setPos(3)
    recorder.trim_start_line.setPos(1)
    recorder.speed_combo.addItem('2x', 2.0)
    recorder.speed_combo.setCurrentIndex(1)
    output = tmp_path / '音声.wav'
    monkeypatch.setattr(main.QFileDialog, 'getSaveFileName', lambda *args: (str(output), ''))
    recorder.save_audio()
    rate, pcm = wavfile.read(output)
    assert rate == 96000
    assert pcm.dtype == np.int16
    assert pcm.tolist() == [[32767, -32767], [16383, -16383]]


def test_duplicate_devices_keep_actual_index(app, monkeypatch, tmp_path):
    device = {'name': 'Same name', 'max_input_channels': 1, 'hostapi': 0}
    devices = [device.copy(), device.copy()]
    monkeypatch.setattr(main.sd, 'query_devices', lambda index=None: devices if index is None else devices[index])
    monkeypatch.setattr(main.sd, 'query_hostapis', lambda: [{'name': 'WASAPI'}])
    settings = QSettings(str(tmp_path / 'devices.ini'), QSettings.Format.IniFormat)
    dialog = main.SettingsDialog(settings)
    assert dialog.device_combo.itemData(0) == 0
    assert dialog.device_combo.itemData(1) == 1
    assert 'WASAPI' in dialog.device_combo.itemText(1)
    dialog.close()


def test_pc_playback_source_uses_loopback_and_preserves_stereo(recorder, monkeypatch):
    recorder.settings.setValue('audio_device', main.LOOPBACK_DEVICE)
    info = {'name': 'PC playback', 'max_input_channels': 2, 'default_samplerate': 48000}
    monkeypatch.setattr(main, 'loopback_info', lambda: info)
    stream = Mock(error=None)
    factory = Mock(return_value=stream)
    monkeypatch.setattr(main, 'LoopbackStream', factory)
    recorder.toggle_record()
    assert recorder.is_recording
    factory.assert_called_once_with(info, recorder.audio_callback)
    data = np.array([[0.25, -0.5]], dtype=np.float32)
    recorder.audio_callback(data, 1, None, None)
    recorder.toggle_record()
    np.testing.assert_array_equal(recorder.audio_data, data)
    stream.stop.assert_called_once()
    stream.close.assert_called_once()


def test_loopback_runtime_error_stops_recording_and_keeps_audio(recorder, monkeypatch):
    recorder.is_recording = True
    recorder.stream = Mock(error=RuntimeError('device unplugged'))
    warning = Mock()
    monkeypatch.setattr(main.QMessageBox, 'warning', warning)
    data = np.array([[0.3, 0.4]], dtype=np.float32)
    recorder.audio_queue.put(data)
    recorder.update_ui()
    assert not recorder.is_recording
    assert recorder.stream is None
    np.testing.assert_array_equal(recorder.audio_data, data)
    warning.assert_called_once()


def test_play_cursor_tracks_trim_range_and_speed_and_hides_on_stop(recorder, monkeypatch):
    recorder.sample_rate = 48000
    recorder.audio_data = np.zeros((144000, 2), dtype=np.float32)
    recorder.trim_end_line.setPos(108000)
    recorder.trim_start_line.setPos(12000)
    recorder.speed_combo.addItem('2x', 2.0)
    recorder.speed_combo.setCurrentIndex(1)
    monkeypatch.setattr(main.sd, 'play', Mock())
    now = [100.0]
    monkeypatch.setattr(main.time, 'monotonic', lambda: now[0])
    assert not recorder.play_cursor.isVisible()
    recorder.toggle_play()
    assert recorder.play_cursor.isVisible()
    assert recorder.play_cursor.value() == 12000
    now[0] += 0.25
    recorder.update_ui()
    assert recorder.play_cursor.value() == 36000
    now[0] += 2
    recorder.update_ui()
    assert recorder.play_cursor.value() == 108000
    recorder.auto_stop_playback()
    assert not recorder.play_cursor.isVisible()
