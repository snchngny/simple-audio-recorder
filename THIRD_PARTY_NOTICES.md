# 利用ライブラリ

本アプリは GPL-3.0-only で公開。配布物にはビルド時点の依存版一覧
`environment.txt` と、各パッケージのライセンス本文 `THIRD_PARTY_LICENSES.txt` を同梱する
（Windowsは `_internal/`、Macはアプリ内のリソース領域）

| 構成 | ライセンス・ソース入口 |
| --- | --- |
| PyQt6 | GPLv3 / 商用。本配布はGPL版。[Riverbank](https://www.riverbankcomputing.com/software/pyqt/)・[ソース配布](https://pypi.org/project/PyQt6/#files) |
| Qt | LGPLv3 / GPL / 商用、同梱モジュールの条件に従う。[ライセンス](https://doc.qt.io/qt-6/licensing.html)・[Qtソース](https://download.qt.io/archive/qt/) |
| PyQt6-sip | [ソース・ライセンス](https://pypi.org/project/PyQt6-sip/) |
| sounddevice / PortAudio | MIT系。[sounddevice](https://github.com/spatialaudio/python-sounddevice)・[PortAudio](https://github.com/PortAudio/portaudio) |
| SoundCard（Windowsのみ） | BSD-3-Clause。[ソース](https://github.com/bastibe/SoundCard) |
| NumPy | BSD系。[ソース](https://github.com/numpy/numpy) |
| SciPy | BSD系および同梱数値計算ライブラリの条件。[ソース](https://github.com/scipy/scipy) |
| pyqtgraph | MIT。[ソース](https://github.com/pyqtgraph/pyqtgraph) |
| CFFI / pycparser | MIT / BSD系。[CFFI](https://foss.heptapod.net/pypy/cffi)・[pycparser](https://github.com/eliben/pycparser) |
| Python | PSF等。[ソース](https://www.python.org/downloads/source/) |
| PyInstallerブートローダー | GPL＋配布例外。[ソース・例外](https://pyinstaller.org/en/stable/license.html) |

対応するアプリのソースとビルド手順は同じタグのGitHub Releaseから取得できる
ライブラリの正確な版は配布物内の `environment.txt` を参照
