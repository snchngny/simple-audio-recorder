"""速度と音程を一緒に変え、一般的なWAVレートへ変換する。"""
from fractions import Fraction

import numpy as np
from scipy.signal import resample_poly

EXPORT_RATE = 48000


def render_sample(samples, source_rate, speed, output_rate=EXPORT_RATE):
    if source_rate <= 0 or output_rate <= 0 or not np.isfinite(speed) or speed <= 0:
        raise ValueError('サンプルレートと速度には正の値が必要です')
    ratio = Fraction(output_rate, source_rate) / Fraction(str(speed)).limit_denominator(1000)
    if ratio == 1:
        return samples
    return resample_poly(samples, ratio.numerator, ratio.denominator, axis=0).astype(np.float32)
