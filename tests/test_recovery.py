import numpy as np

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
