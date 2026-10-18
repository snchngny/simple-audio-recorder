import sys
import os
import queue
import datetime
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
import pyqtgraph as pg
from loopback import LOOPBACK_DEVICE, LoopbackStream, loopback_info

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QPushButton, QLabel, QComboBox, QFileDialog, 
    QMessageBox, QDialog, QDialogButtonBox, QStatusBar
)
from PyQt6.QtCore import QTimer, QSettings, Qt, pyqtSignal

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.settings = settings
        
        layout = QVBoxLayout(self)
        
        # Audio Device
        dev_layout = QHBoxLayout()
        dev_layout.addWidget(QLabel("入力デバイス:"))
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self.update_channels)
        dev_layout.addWidget(self.device_combo)
        layout.addLayout(dev_layout)
        
        # Audio Channel
        ch_layout = QHBoxLayout()
        ch_layout.addWidget(QLabel("L Ch:"))
        self.channel_l_combo = QComboBox()
        ch_layout.addWidget(self.channel_l_combo)
        
        ch_layout.addWidget(QLabel("R Ch:"))
        self.channel_r_combo = QComboBox()
        ch_layout.addWidget(self.channel_r_combo)
        layout.addLayout(ch_layout)
        
        # Save Directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("保存先:"))
        self.dir_label = QLabel()
        
        default_dir = os.path.expanduser("~/Downloads")
        saved_dir = self.settings.value("save_dir", defaultValue=default_dir)
        if not os.path.exists(saved_dir):
            saved_dir = default_dir
        self.current_dir = saved_dir
        
        self.dir_label.setText(self.current_dir)
        dir_btn = QPushButton("参照...")
        dir_btn.clicked.connect(self.browse_dir)
        
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(dir_btn)
        layout.addLayout(dir_layout)
        
        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.populate_devices()
        
    def populate_devices(self):
        try:
            devices = sd.query_devices()
            input_devices = [(idx, d) for idx, d in enumerate(devices) if d['max_input_channels'] > 0]
            hostapis = sd.query_hostapis()
            
            saved_device = self.settings.value("audio_device", defaultValue=-1, type=int)
            default_device_idx = sd.default.device[0]
            target_device_idx = saved_device if saved_device is not None and saved_device != -1 else default_device_idx
            
            selected_idx = 0
            self.device_combo.blockSignals(True)
            for i, (actual_idx, d) in enumerate(input_devices):
                host = hostapis[d['hostapi']]['name']
                self.device_combo.addItem(f"{d['name']} / {host} ({d['max_input_channels']}ch)", actual_idx)
                if actual_idx == target_device_idx:
                    selected_idx = i
            if sys.platform == 'win32':
                if target_device_idx == LOOPBACK_DEVICE:
                    selected_idx = self.device_combo.count()
                self.device_combo.addItem('PC再生音（既定の出力 / WASAPI）', LOOPBACK_DEVICE)
                    
            self.device_combo.setCurrentIndex(selected_idx)
            self.device_combo.blockSignals(False)
            self.update_channels()
            if not self.device_combo.count():
                self.device_combo.addItem("入力デバイスがありません", None)
        except Exception as e:
            self.device_combo.addItem(f"デバイス取得エラー: {e}", None)

    def update_channels(self):
        self.channel_l_combo.clear()
        self.channel_r_combo.clear()
        device_idx = self.device_combo.currentData()
        if device_idx is None:
            return
            
        try:
            device_info = loopback_info() if device_idx == LOOPBACK_DEVICE else sd.query_devices(device_idx)
            max_channels = device_info['max_input_channels']
            
            # Use max(..., 0) to avoid negative defaults if max_channels is 0 somehow
            saved_l = self.settings.value("audio_channel_l", defaultValue=0, type=int)
            saved_r = self.settings.value("audio_channel_r", defaultValue=max(0, min(1, max_channels - 1)), type=int)
            
            target_l_idx = 0
            target_r_idx = 0
            for i in range(max_channels):
                self.channel_l_combo.addItem(f"CH {i+1}", i)
                self.channel_r_combo.addItem(f"CH {i+1}", i)
                if i == saved_l: target_l_idx = i
                if i == saved_r: target_r_idx = i
                    
            self.channel_l_combo.setCurrentIndex(target_l_idx)
            self.channel_r_combo.setCurrentIndex(target_r_idx)
        except Exception as e:
            pass

    def browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "保存先を選択", self.current_dir)
        if d:
            self.current_dir = d
            self.dir_label.setText(d)
            
    def get_settings(self):
        return {
            "device_idx": self.device_combo.currentData(),
            "channel_l": self.channel_l_combo.currentData(),
            "channel_r": self.channel_r_combo.currentData(),
            "save_dir": self.current_dir
        }


class AudioRecorder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Audio Recorder (Stereo)")
        self.resize(600, 250)
        
        self.settings = QSettings("com.python.audiorec", "SimpleAudioRecorder")
        
        # State
        self.is_recording = False
        self.is_playing = False
        self.sample_rate = 44100
        
        # Stereo Audio Data (N, 2)
        self.audio_data = np.zeros((0, 2), dtype=np.float32)
        self.recorded_chunks = []
        self.total_recorded_samples = 0
        self.audio_queue = queue.Queue()
        self.stream = None
        self.current_channel_l = 0
        self.current_channel_r = 1
        
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("待機中...")

        # Central Layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Plot
        pg.setConfigOption('background', '#f5f5f5')
        pg.setConfigOption('foreground', '#333')
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        
        # Single curve for waveform display (mixdown of L+R)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='#2196F3', width=1.5))
        
        # Trim Lines
        self.trim_start_line = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen(color='#4CAF50', width=2))
        self.trim_end_line = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen(color='#F44336', width=2))
        self.plot_widget.addItem(self.trim_start_line)
        self.plot_widget.addItem(self.trim_end_line)
        self.trim_start_line.sigPositionChanged.connect(self.on_trim_changed)
        self.trim_end_line.sigPositionChanged.connect(self.on_trim_changed)
        
        self.update_trim_lines_visibility(False)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        
        self.rec_btn = QPushButton("🔴 録音")
        self.rec_btn.setStyleSheet("font-weight: bold;")
        self.rec_btn.clicked.connect(self.toggle_record)
        ctrl_layout.addWidget(self.rec_btn)
        
        self.play_btn = QPushButton("▶️ 再生 (トリミング範囲)")
        self.play_btn.clicked.connect(self.toggle_play)
        self.play_btn.setEnabled(False)
        ctrl_layout.addWidget(self.play_btn)
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self.save_audio)
        self.save_btn.setEnabled(False)
        ctrl_layout.addWidget(self.save_btn)
        
        # Speed controls
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("速度:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItem("Default (1.0x)", 1.0)
        self.speed_combo.currentIndexChanged.connect(self.on_trim_changed)
        speed_layout.addWidget(self.speed_combo)
        
        self.rnd_speed_btn = QPushButton("🎲 ランダム速度")
        self.rnd_speed_btn.clicked.connect(self.randomize_speed)
        speed_layout.addWidget(self.rnd_speed_btn)
        
        ctrl_layout.addLayout(speed_layout)
        
        ctrl_layout.addStretch()
        
        self.settings_btn = QPushButton("⚙️ 設定")
        self.settings_btn.clicked.connect(self.open_settings)
        ctrl_layout.addWidget(self.settings_btn)
        
        layout.addLayout(ctrl_layout)
        
        # Timer for UI update
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)
        
    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            opts = dlg.get_settings()
            self.settings.setValue("audio_device", opts["device_idx"])
            self.settings.setValue("audio_channel_l", opts["channel_l"])
            self.settings.setValue("audio_channel_r", opts["channel_r"])
            self.settings.setValue("save_dir", opts["save_dir"])
            self.status.showMessage("設定を保存しました", 3000)
            
    def randomize_speed(self):
        import random
        new_speed = round(random.uniform(1.1, 3.0), 2)
        label = f"Random ({new_speed}x)"
        self.speed_combo.addItem(label, new_speed)
        self.speed_combo.setCurrentIndex(self.speed_combo.count() - 1)
            
    def toggle_record(self):
        if not self.is_recording:
            # Stop any playback
            if self.is_playing:
                self.auto_stop_playback()
                
            self.audio_data = np.zeros((0, 2), dtype=np.float32)
            self.recorded_chunks = []
            self.total_recorded_samples = 0
            self.curve.setData([])
            self.update_trim_lines_visibility(False)
            
            # Load Device Settings
            device_idx = self.settings.value("audio_device", defaultValue=-1, type=int)
            if device_idx is None or device_idx == -1:
                try: device_idx = sd.default.device[0]
                except: device_idx = None
                
            channel_l = self.settings.value("audio_channel_l", defaultValue=0, type=int)
            channel_r = self.settings.value("audio_channel_r", defaultValue=1, type=int)
                
            try:
                is_loopback = device_idx == LOOPBACK_DEVICE
                device_info = loopback_info() if is_loopback else sd.query_devices(device_idx, 'input')
                max_channels = device_info['max_input_channels']
                if max_channels < 1:
                    raise ValueError("入力チャンネルがありません。設定から入力デバイスを選択してください")
                # Use the device's native rate (often 48 kHz on Windows).
                self.sample_rate = int(device_info['default_samplerate'])
                if not is_loopback:
                    sd.check_input_settings(device=device_idx, channels=max_channels,
                                            samplerate=self.sample_rate, dtype='float32')
                
                # Boundary check for channel index
                if channel_l >= max_channels or channel_l < 0: channel_l = 0
                if channel_r >= max_channels or channel_r < 0: channel_r = max(0, min(1, max_channels - 1))
                    
                self.current_channel_l = channel_l
                self.current_channel_r = channel_r

                # Start stream fetching ALL channels to prevent CoreAudio slicing issues
                self.stream = LoopbackStream(device_info, self.audio_callback) if is_loopback else sd.InputStream(
                    device=device_idx,
                    channels=max_channels,
                    samplerate=self.sample_rate,
                    dtype='float32',
                    callback=self.audio_callback
                )
                self.stream.start()
                self.settings_btn.setEnabled(False)
                self.is_recording = True
                self.rec_btn.setText("⏹ 録音停止")
                self.rec_btn.setStyleSheet("color: red; font-weight: bold;")
                self.status.showMessage(f"🔴 録音中... デバイス: {device_info['name']} (L:CH {channel_l + 1}, R:CH {channel_r + 1})")
                
                self.play_btn.setEnabled(False)
                self.save_btn.setEnabled(False)
            except Exception as e:
                if self.stream is not None:
                    self.stream.close()
                    self.stream = None
                QMessageBox.critical(self, "エラー", f"オーディオデバイスの初期化に失敗しました:\n{e}")
        else:
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                
            self.is_recording = False
            self.settings_btn.setEnabled(True)
            self.rec_btn.setText("🔴 録音")
            self.rec_btn.setStyleSheet("font-weight: bold;")
            
            # Drain queue
            self.drain_queue()
            
            if self.recorded_chunks:
                self.audio_data = np.concatenate(self.recorded_chunks, axis=0)
            else:
                self.audio_data = np.zeros((0, 2), dtype=np.float32)
            
            if len(self.audio_data) > 0:
                # Update UI with full waveform downsampled for performance
                mono_mix = np.mean(self.audio_data, axis=1)
                step = max(1, len(mono_mix) // 5000)
                x_axis = np.arange(len(mono_mix))
                self.curve.setData(x=x_axis[::step], y=mono_mix[::step])
                
                self.update_trim_lines_visibility(True)
                self.trim_start_line.setPos(0)
                self.trim_end_line.setPos(len(self.audio_data))
                self.plot_widget.setXRange(0, len(self.audio_data))
                self.play_btn.setEnabled(True)
                self.save_btn.setEnabled(True)
                
                dur = len(self.audio_data) / self.sample_rate
                
                # Check for macOS absolute silence (Microphone Permission Issue)
                if np.max(np.abs(self.audio_data)) < 0.0001:
                    self.status.showMessage("⚠️ 無音です。OSのマイク権限と設定の入力デバイス・L/R割当を確認してください")
                else:
                    self.status.showMessage(f"録音完了 {dur:.1f}秒。緑と赤の線をドラッグしてトリミング長を調整できます。")

    def update_trim_lines_visibility(self, visible):
        self.trim_start_line.setVisible(visible)
        self.trim_end_line.setVisible(visible)

    def on_trim_changed(self):
        if len(self.audio_data) == 0:
            return
        
        start = self.trim_start_line.value()
        end = self.trim_end_line.value()
        
        # Enforce constraints
        if start < 0:
            self.trim_start_line.setPos(0)
        elif start > len(self.audio_data) - 1:
            self.trim_start_line.setPos(len(self.audio_data) - 1)
            
        if end > len(self.audio_data):
            self.trim_end_line.setPos(len(self.audio_data))
        elif end < 1:
            self.trim_end_line.setPos(1)
            
        # Ensure start < end
        start = self.trim_start_line.value()
        end = self.trim_end_line.value()
        if start >= end:
            if self.sender() == self.trim_start_line:
                self.trim_start_line.setPos(end - 1)
            else:
                self.trim_end_line.setPos(start + 1)
                
        # Status update
        if not self.is_recording and hasattr(self, 'speed_combo'):
            s_idx = max(0, min(int(self.trim_start_line.value()), len(self.audio_data)))
            e_idx = max(0, min(int(self.trim_end_line.value()), len(self.audio_data)))
            speed = self.speed_combo.currentData()
            dur = (e_idx - s_idx) / (self.sample_rate * speed)
            if dur > 0:
                self.status.showMessage(f"トリミング範囲: {dur:.2f}秒 (Stereo, 速度: {speed}x)")


    def audio_callback(self, indata, frames, time, status):
        # Prevent index out of bounds if something weird happens
        safe_l_idx = min(self.current_channel_l, indata.shape[1] - 1)
        safe_r_idx = min(self.current_channel_r, indata.shape[1] - 1)
        # Extract stereo frame
        stereo_frame = indata[:, [safe_l_idx, safe_r_idx]].copy()
        self.audio_queue.put(stereo_frame)

    def drain_queue(self):
        chunks = []
        while not self.audio_queue.empty():
            try:
                chunks.append(self.audio_queue.get_nowait())
            except queue.Empty:
                break
        if chunks:
            new_data = np.concatenate(chunks, axis=0)
            self.recorded_chunks.append(new_data)
            self.total_recorded_samples += len(new_data)
            return True
        return False

    def update_ui(self):
        error = getattr(self.stream, 'error', None)
        if self.is_recording and isinstance(error, Exception):
            self.toggle_record()
            QMessageBox.warning(self, '録音が中断されました', str(error))
            return
        if self.is_recording:
            if self.drain_queue():
                view_len = self.sample_rate * 5
                recent_chunks = []
                samples_collected = 0
                for chunk in reversed(self.recorded_chunks):
                    recent_chunks.append(chunk)
                    samples_collected += len(chunk)
                    if samples_collected >= view_len:
                        break
                
                recent_chunks.reverse()
                if recent_chunks:
                    display_data = np.concatenate(recent_chunks, axis=0)
                    if len(display_data) > view_len:
                        display_data = display_data[-view_len:]
                    
                    mono_mix = np.mean(display_data, axis=1)
                    data_len = self.total_recorded_samples
                    start_x = max(0, data_len - len(display_data))
                    x_axis = np.arange(start_x, start_x + len(display_data))
                    
                    step = max(1, len(mono_mix) // 2000)
                    self.curve.setData(x=x_axis[::step], y=mono_mix[::step])
                    self.plot_widget.setXRange(max(0, data_len - view_len), max(view_len, data_len))

    def get_trimmed_data(self):
        if len(self.audio_data) == 0:
            return None
        start = int(self.trim_start_line.value())
        end = int(self.trim_end_line.value())
        start = max(0, min(start, len(self.audio_data) - 1))
        end = max(0, min(end, len(self.audio_data)))
        return self.audio_data[start:end]

    def toggle_play(self):
        if not self.is_playing:
            trimmed = self.get_trimmed_data()
            if trimmed is None or len(trimmed) == 0:
                return
            
            try:
                speed = self.speed_combo.currentData()
                play_rate = int(self.sample_rate * speed)
                
                # Play stereo data
                sd.play(trimmed, play_rate)
                self.is_playing = True
                self.play_btn.setText("⏹ 停止")
                
                # Auto stop logic
                duration_ms = int((len(trimmed) / play_rate) * 1000)
                self.play_timer = QTimer()
                self.play_timer.setSingleShot(True)
                self.play_timer.timeout.connect(self.auto_stop_playback)
                self.play_timer.start(duration_ms)
                
                self.status.showMessage(f"ステレオ再生中... (速度: {speed}x)")
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"再生エラー:\n{e}")
        else:
            self.auto_stop_playback()

    def auto_stop_playback(self):
        sd.stop()
        self.is_playing = False
        self.play_btn.setText("▶️ 再生 (トリミング範囲)")
        if hasattr(self, 'play_timer'):
            self.play_timer.stop()
        self.status.showMessage("再生停止")

    def save_audio(self):
        trimmed = self.get_trimmed_data()
        if trimmed is None or len(trimmed) == 0:
            return
            
        default_dir = os.path.expanduser("~/Downloads")
        saved_dir = self.settings.value("save_dir", defaultValue=default_dir)
        if not os.path.exists(saved_dir):
            saved_dir = default_dir
            
        # Format filename
        now = datetime.datetime.now()
        filename = f"Recording_Stereo_{now.strftime('%Y%m%d_%H%M%S')}.wav"
        save_path = os.path.join(saved_dir, filename)
        
        filepath, _ = QFileDialog.getSaveFileName(self, "保存", save_path, "WAV Files (*.wav)")
        if filepath:
            try:
                speed = self.speed_combo.currentData()
                save_rate = int(self.sample_rate * speed)
                # Multiply by 32767 and cast to int16 for standard WAV format
                scaled = np.clip(trimmed, -1.0, 1.0) # Prevent clipping wrap-around
                scaled = np.int16(scaled * 32767) # Shape is (N, 2), wavfile can handle it properly!
                wavfile.write(filepath, save_rate, scaled)
                self.status.showMessage(f"保存しました: {os.path.basename(filepath)} (速度: {speed}x)", 7000)
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"保存に失敗しました:\n{e}")

    def closeEvent(self, event):
        self.timer.stop()
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        sd.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = AudioRecorder()
    window.show()
    if '--smoke-test' in sys.argv:
        # Exercise the packaged Qt plugins and PortAudio without opening a microphone.
        sd.query_hostapis()
        QTimer.singleShot(200, app.quit)
    sys.exit(app.exec())
