import numpy as np
import subprocess
import sys
from unittest.mock import Mock
import recovery

from recovery import RecordingJournal, find_recordings


def test_recovery_ignores_partial_frame_and_preserves_stereo(tmp_path):
    journal = RecordingJournal(tmp_path, 48000)
    journal.start()
    data = np.array([[0.25, -0.5], [0.1, 0.2]], dtype=np.float32)
    journal.append(data)
    journal.close()
    journal.lock.unlock()  # 前のプロセスの終了を模擬
    with journal.path.open('ab') as writer:
        writer.write(b'bad')
    recovered = find_recordings(tmp_path)
    assert len(recovered) == 1
    samples = recovered[0].read()
    np.testing.assert_array_equal(samples, data)
    samples._mmap.close()
    recovered[0].discard()
    assert not list(tmp_path.glob('*.raw'))


def test_active_recording_is_not_offered_to_another_instance(tmp_path):
    journal = RecordingJournal(tmp_path, 44100)
    journal.start()
    journal.append(np.ones((2, 2), dtype=np.float32))
    assert find_recordings(tmp_path) == []
    journal.discard()


def test_abrupt_process_exit_leaves_recoverable_audio(tmp_path):
    script = '''import os, sys
import numpy as np
from recovery import RecordingJournal
journal = RecordingJournal(sys.argv[1], 48000)
journal.start()
journal.append(np.full((4800, 2), 0.25, dtype=np.float32))
os._exit(0)
'''
    subprocess.run([sys.executable, '-c', script, str(tmp_path)], check=True)
    candidates = find_recordings(tmp_path)
    assert len(candidates) == 1
    data = candidates[0].read()
    assert len(data) == 4800
    np.testing.assert_array_equal(data, np.full((4800, 2), 0.25, dtype=np.float32))
    data._mmap.close()
    candidates[0].discard()


def test_failed_disk_sync_preserves_readable_frames(tmp_path, monkeypatch):
    journal = RecordingJournal(tmp_path, 48000)
    journal.start()
    data = np.full((10, 2), 0.25, dtype=np.float32)
    journal.append(data)
    monkeypatch.setattr(recovery.os, 'fsync', Mock(side_effect=OSError('disk full')))
    samples = journal.read()
    assert isinstance(journal.error, OSError)
    assert journal.writer is None
    np.testing.assert_array_equal(samples, data)
    samples._mmap.close()
    journal.discard()
