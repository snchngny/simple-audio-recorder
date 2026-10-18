"""端末内だけに保持する録音の復旧用float32ジャーナル。"""
import json
import os
from pathlib import Path
import uuid

import numpy as np
from PyQt6.QtCore import QLockFile


class RecordingJournal:
    def __init__(self, directory, sample_rate, recording_id=None):
        self.directory = Path(directory)
        self.recording_id = recording_id or uuid.uuid4().hex
        if len(self.recording_id) != 32 or any(c not in '0123456789abcdef' for c in self.recording_id):
            raise ValueError('不正な録音IDです')
        self.sample_rate = int(sample_rate)
        if not 8000 <= self.sample_rate <= 384000:
            raise ValueError('不正な録音レートです')
        self.path = self.directory / f'{self.recording_id}.raw'
        self.metadata = self.directory / f'{self.recording_id}.json'
        self.writer = None
        self.owns_files = False
        self.lock = QLockFile(str(self.directory / f'{self.recording_id}.lock'))
        self.lock.setStaleLockTime(0)

    def start(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.lock.tryLock(0):
            raise RuntimeError('録音キャッシュが使用中です')
        self.writer = self.path.open('xb')
        self.owns_files = True
        self.metadata.write_text(json.dumps({'sample_rate': self.sample_rate}), encoding='utf-8')

    def append(self, data):
        self.writer.write(np.asarray(data, dtype='<f4').tobytes())
        # OSへ渡し、プロセス異常終了でも書込み済み部分を復旧できるようにする
        self.writer.flush()

    def close(self):
        if self.writer is not None:
            try:
                self.writer.flush()
                os.fsync(self.writer.fileno())
            finally:
                self.writer.close()
                self.writer = None

    def read(self):
        self.close()
        # 異常終了時の半端な最終フレームは読み込まない
        frames = self.path.stat().st_size // 8
        if not frames:
            return np.zeros((0, 2), dtype=np.float32)
        return np.memmap(self.path, dtype='<f4', mode='r', shape=(frames, 2))

    def discard(self):
        self.close()
        if self.owns_files:
            self.path.unlink(missing_ok=True)
            self.metadata.unlink(missing_ok=True)
        self.lock.unlock()


def find_recordings(directory):
    recordings = []
    for metadata in sorted(Path(directory).glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            rate = json.loads(metadata.read_text(encoding='utf-8'))['sample_rate']
            journal = RecordingJournal(directory, rate, metadata.stem)
            if journal.path.stat().st_size >= 8 and journal.lock.tryLock(0):
                journal.owns_files = True
                recordings.append(journal)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return recordings
