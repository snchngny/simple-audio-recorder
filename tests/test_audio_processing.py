import numpy as np
import pytest

from audio_processing import EXPORT_RATE, render_sample


@pytest.mark.parametrize('source_rate,speed', [(48000, 1.0), (48000, 2.0), (44100, 1.73), (48000, 0.5)])
def test_speed_changes_duration_and_pitch_at_standard_rate(source_rate, speed):
    t = np.arange(source_rate, dtype=np.float32) / source_rate
    tone = np.sin(2 * np.pi * 440 * t)
    original = np.column_stack([tone, -tone])
    rendered = render_sample(original, source_rate, speed)
    assert abs(len(rendered) - EXPORT_RATE / speed) <= 1
    spectrum = np.abs(np.fft.rfft(rendered[:, 0]))
    peak = np.argmax(spectrum) * EXPORT_RATE / len(rendered)
    assert abs(peak - 440 * speed) < 3
    np.testing.assert_allclose(rendered[:, 0], -rendered[:, 1], atol=1e-6)
    np.testing.assert_array_equal(original[:, 0], tone)


def test_unity_speed_preserves_exact_samples():
    data = np.array([[0.25, -0.5], [1, -1]], dtype=np.float32)
    np.testing.assert_array_equal(render_sample(data, 48000, 1), data)
