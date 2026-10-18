"""自作合成音を使い、実際のQt画面からStore向けPNGを作る。"""
import os
from pathlib import Path
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont, QFontDatabase, QFontMetrics
from PyQt6.QtWidgets import QApplication
from main import AudioRecorder


def main():
    output = ROOT / 'dist/store-assets'
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    # offscreenのWindows Qtは既定フォントだけでは日本語が欠けることがある
    japanese_font = Path(os.environ.get('STORE_SCREENSHOT_FONT') or
                         str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/meiryo.ttc'))
    if japanese_font.is_file():
        font_id = QFontDatabase.addApplicationFont(str(japanese_font))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            raise RuntimeError('画像用フォントを読み込めませんでした')
        app.setFont(QFont(families[0], 10))
    if not all(QFontMetrics(app.font()).inFontUcs4(ord(char)) for char in '録音保存速度'):
        raise RuntimeError('日本語を描画できません。STORE_SCREENSHOT_FONTに日本語フォントを指定してください')
    app.setStyle('Fusion')
    window = AudioRecorder(recovery_dir=ROOT / 'build/screenshot-recovery', restore=False)
    window.settings = QSettings(str(ROOT / 'build/screenshot-settings.ini'), QSettings.Format.IniFormat)
    window.resize(1366, 768)
    window.sample_rate = 48000
    t = np.arange(48000 * 8, dtype=np.float32) / 48000
    rng = np.random.default_rng(42)
    envelope = np.exp(-((t % 1.7) * 6))
    signal = (0.42 * np.sin(2 * np.pi * (180 * t + 35 * np.sin(t * 2))) +
              0.15 * rng.normal(size=len(t))) * envelope
    window.audio_data = np.column_stack((signal, signal * 0.8)).astype(np.float32)
    window.show_recording()
    window.trim_start_line.setPos(48000)
    window.trim_end_line.setPos(48000 * 6)
    window.status.showMessage('自作合成音から範囲を選択。ランダム速度で別のサンプルを試せます')
    window.show()
    app.processEvents()
    window.grab().save(str(output / '01-trim.png'))
    window.speed_combo.addItem('ランダム 1.73倍', 1.73)
    window.speed_combo.setCurrentIndex(1)
    window.status.showMessage('元録音は保持。1.73倍の速度・音程で加工し、48kHz WAVへ保存')
    app.processEvents()
    window.grab().save(str(output / '02-random-speed.png'))
    window.dirty = False
    window.close()
    print(f'実画面PNG（合成音、個人情報なし）: {output}')


if __name__ == '__main__':
    main()
