"""Windowsセットアップexe / macOS DMGを、実行中OS用に生成する。"""
from pathlib import Path
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
NAME = 'SimpleAudioRecorder'


def run(*args, env=None):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True, env=env)


def main():
    os.chdir(ROOT)
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('VERSIONには major.minor.patch を指定してください')
    if platform.system() not in ('Windows', 'Darwin'):
        raise RuntimeError('Windows または macOS で実行してください')
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    inputs = ('main.py', 'audio_processing.py', 'recovery.py', 'loopback.py',
              'requirements.txt', 'requirements-build.txt', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
              'PRIVACY.md', 'VERSION', 'packaging/build.py')
    source_hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in inputs}
    notices = build / 'THIRD_PARTY_LICENSES.txt'
    run(sys.executable, '-m', 'piplicenses', '--format=plain-vertical',
        '--with-license-file', '--no-license-path',
        '--output-file', notices,
        '--packages', 'PyQt6', 'PyQt6-Qt6', 'PyQt6-sip', 'sounddevice',
        'numpy', 'scipy', 'pyqtgraph', 'cffi', 'pycparser', 'colorama', 'SoundCard')
    freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (build / 'environment.txt').write_text(freeze, encoding='utf-8')
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
            '--windowed', '--name', NAME, '--specpath', str(build),
            '--workpath', str(build / 'pyinstaller'), '--distpath', str(ROOT / 'dist'),
            '--add-data', f'{ROOT / "LICENSE"}:.',
            '--add-data', f'{ROOT / "THIRD_PARTY_NOTICES.md"}:.',
            '--add-data', f'{ROOT / "PRIVACY.md"}:.',
            '--add-data', f'{ROOT / "VERSION"}:.',
            '--add-data', f'{notices}:.', '--add-data', f'{build / "environment.txt"}:.']
    if sys.platform == 'darwin':
        args += ['--osx-bundle-identifier', 'com.snchngny.simple-audio-recorder']
    build_env = os.environ.copy()
    if sys.platform == 'win32':
        # Foreign DLLs on PATH (e.g. Poppler's ICU) can shadow Windows' ICU
        # during dependency analysis even when the source app runs correctly.
        windows = Path(os.environ['WINDIR'])
        build_env['PATH'] = os.pathsep.join([
            str(Path(sys.executable).parent), sys.base_prefix,
            str(windows / 'System32'), str(windows),
        ])
    run(*args, ROOT / 'main.py', env=build_env)
    if sys.platform == 'win32':
        if any(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected
               for path, expected in source_hashes.items()):
            raise RuntimeError('ビルド中にソースが変わりました。再ビルドしてください')
        provenance = {'version': version, 'inputs': source_hashes}
        (ROOT / 'dist' / NAME / 'bundle-info.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
        if '--bundle-only' in sys.argv:
            return
        compiler = shutil.which('ISCC')
        if not compiler:
            for base in (os.environ.get('ProgramFiles(x86)'), os.environ.get('LOCALAPPDATA')):
                if base:
                    for suffix in ('Inno Setup 6/ISCC.exe', 'Programs/Inno Setup 6/ISCC.exe'):
                        candidate = Path(base) / suffix
                        if candidate.is_file():
                            compiler = str(candidate)
                            break
        if not compiler:
            raise RuntimeError('Inno Setup 6 をインストールしてください（ISCCが見つかりません）')
        run(compiler, f'/DAppVersion={version}', ROOT / 'packaging/windows.iss')
    else:
        app = ROOT / 'dist' / f'{NAME}.app'
        info = app / 'Contents/Info.plist'
        with info.open('rb') as f:
            metadata = plistlib.load(f)
        metadata.update(CFBundleShortVersionString=version,
                        CFBundleVersion=os.environ.get('GITHUB_RUN_NUMBER', version),
                        NSMicrophoneUsageDescription='録音のためにマイクへアクセスします')
        with info.open('wb') as f:
            plistlib.dump(metadata, f)
        run('codesign', '--force', '--deep', '--sign', '-', app)
        run('codesign', '--verify', '--deep', '--strict', app)
        if '--bundle-only' in sys.argv:
            return
        stage = build / 'dmg'
        stage.mkdir(exist_ok=True)
        staged_app = stage / app.name
        if staged_app.exists():
            raise RuntimeError('build/dmg が残っています。内容を確認してから別の出力先へ退避してください')
        shutil.copytree(app, staged_app, symlinks=True)
        (stage / 'Applications').symlink_to('/Applications')
        run('hdiutil', 'create', '-volname', 'Simple Sample Recorder',
            '-srcfolder', stage, '-ov', '-format', 'UDZO',
            ROOT / 'dist' / f'{NAME}-v{version}-macos-{platform.machine()}.dmg')


if __name__ == '__main__':
    main()
