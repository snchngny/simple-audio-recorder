"""PyInstallerのWindows bundleをStore用MSIXへ梱包する。登録・署名・提出は行わない。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read_identity(path=None, development=False):
    if development:
        return {'identity_name': 'snchngny.SimpleAudioRecorder.Dev', 'publisher': 'CN=snchngny',
                'publisher_display_name': 'snchngny', 'display_name': 'Simple Audio Recorder Preview'}
    if not path:
        raise ValueError('予約後の製品IDを --identity で指定してください。未予約の検証は --development')
    identity = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    for field in ('identity_name', 'publisher', 'publisher_display_name', 'display_name'):
        if not isinstance(identity.get(field), str) or not identity[field].strip():
            raise ValueError(f'{field} はPartner Centerの正確な値が必要です')
    if not re.fullmatch(r'[A-Za-z0-9.-]{3,50}', identity['identity_name']):
        raise ValueError('Package/Identity/Nameの形式が不正です')
    if not identity['publisher'].startswith('CN='):
        raise ValueError('PublisherはPartner CenterのCN=から始まる値を指定してください')
    if identity['identity_name'].endswith('.Dev'):
        raise ValueError('検証用の製品IDを提出用に使用できません')
    return identity


def manifest(identity, version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or any(int(v) > 65535 for v in version.split('.')):
        raise ValueError('VERSIONは各要素0〜65535のmajor.minor.patchが必要です')
    values = {key: escape(value, {'"': '&quot;'}) for key, value in identity.items()}
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
 xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
 xmlns:uap10="http://schemas.microsoft.com/appx/manifest/uap/windows10/10"
 xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
 IgnorableNamespaces="uap uap10 rescap">
 <Identity Name="{values['identity_name']}" Publisher="{values['publisher']}" Version="{version}.0" ProcessorArchitecture="x64"/>
 <Properties><DisplayName>{values['display_name']}</DisplayName><PublisherDisplayName>{values['publisher_display_name']}</PublisherDisplayName><Logo>Assets/StoreLogo.png</Logo></Properties>
 <Resources><Resource Language="ja-JP"/></Resources>
 <Dependencies><TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.26100.0"/></Dependencies>
 <Applications><Application Id="App" Executable="SimpleAudioRecorder.exe" uap10:RuntimeBehavior="packagedClassicApp" uap10:TrustLevel="mediumIL">
 <uap:VisualElements DisplayName="{values['display_name']}" Description="音を録って、切り出して、ランダム速度でサンプル制作" Square150x150Logo="Assets/Square150x150Logo.png" Square44x44Logo="Assets/Square44x44Logo.png" BackgroundColor="#182b42"/>
 </Application></Applications>
 <Capabilities><rescap:Capability Name="runFullTrust"/><DeviceCapability Name="microphone"/></Capabilities>
</Package>
'''


def create_assets(directory):
    from PyQt6.QtCore import QRectF
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer
    directory.mkdir(parents=True, exist_ok=True)
    renderer = QSvgRenderer(str(HERE / 'icon.svg'))
    for filename, size in [('StoreLogo.png', 50), ('Square44x44Logo.png', 44),
                           ('Square150x150Logo.png', 150), ('StoreTile300.png', 300)]:
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        if not image.save(str(directory / filename)):
            raise OSError(f'アイコンの保存に失敗: {filename}')


def find_makeappx(explicit=None):
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    executable = shutil.which('MakeAppx.exe')
    if executable:
        return Path(executable)
    sdk = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Windows Kits/10/bin'
    candidates = sorted(sdk.glob('*/x64/makeappx.exe'), reverse=True)
    if candidates:
        return candidates[0]
    raise FileNotFoundError('Windows SDKのMakeAppx.exeが必要です。--makeappx で場所を指定できます')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', type=Path)
    parser.add_argument('--development', action='store_true', help='予約不要の検証用ID。Storeへ提出しない')
    parser.add_argument('--makeappx', type=Path)
    parser.add_argument('--prepare-only', action='store_true', help='manifestとアイコンまで生成する')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Windows x64上で実行してください')
    identity = read_identity(args.identity, args.development)
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if not args.development and status.strip():
        parser.error('提出用は検証・commit済みのclean checkoutで作成してください')
    version = (ROOT / 'VERSION').read_text().strip()
    bundle = ROOT / 'dist/SimpleAudioRecorder'
    if not (bundle / 'SimpleAudioRecorder.exe').is_file():
        parser.error('先に python packaging/build.py --bundle-only を実行してください')
    provenance_file = bundle / 'bundle-info.json'
    if not provenance_file.is_file():
        parser.error('bundleの出典情報がありません。packaging/build.pyで再ビルドしてください')
    provenance = json.loads(provenance_file.read_text(encoding='utf-8'))
    for path, expected in provenance['inputs'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            parser.error(f'bundle作成後に変更があります: {path}。packaging/build.pyで再ビルドしてください')
    if provenance['version'] != version:
        parser.error('bundleの版がVERSIONと一致しません')
    # 出力は所有repoのbuild/distだけ。以前の生成物を再帰削除しない
    stage = ROOT / 'build/msix' / uuid.uuid4().hex
    shutil.copytree(bundle, stage)
    (stage / 'AppxManifest.xml').write_text(manifest(identity, version), encoding='utf-8')
    create_assets(stage / 'Assets')
    (stage / 'LICENSE').write_bytes((ROOT / 'LICENSE').read_bytes())
    (stage / 'PRIVACY.md').write_bytes((ROOT / 'PRIVACY.md').read_bytes())
    if args.prepare_only:
        print(f'MSIX梱包前の資材: {stage}')
        return
    output = ROOT / 'dist' / f'SimpleAudioRecorder-v{version}-windows-x64-{"PREVIEW" if args.development else "store"}.msix'
    log = stage.parent / f'{stage.name}.log'
    with log.open('w', encoding='utf-8') as handle:
        result = subprocess.run([str(find_makeappx(args.makeappx)), 'pack', '/d', str(stage),
                                 '/p', str(output), '/o'], stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text(encoding='utf-8', errors='replace')[-5000:], file=sys.stderr)
        raise RuntimeError(f'MakeAppx検証に失敗しました: {log}')
    final_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    final_status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if final_commit != commit or final_status != status or any(
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected
            for path, expected in provenance['inputs'].items()):
        raise RuntimeError('梱包中にソースが変わりました。このMSIXは提出せず、再ビルドしてください')
    receipt = {'version': version, 'commit': commit, 'dirty': bool(status.strip()),
               'development_identity': args.development, 'identity': identity,
               'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
               'signed': False, 'store_certified': False,
               'note': '未署名。検証用IDは提出不可。正式ID版も署名後の実機検証とStore審査が必要'}
    output.with_suffix('.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    if not status.strip():
        subprocess.run(['git', 'archive', '--format=tar.gz', '--prefix=SimpleAudioRecorder/',
                        '-o', str(output.with_suffix('.source.tar.gz')), 'HEAD'], cwd=ROOT, check=True)
    print(f'MakeAppx検証済み（未署名）: {output}')
    print(f'ログ: {log}')


if __name__ == '__main__':
    main()
