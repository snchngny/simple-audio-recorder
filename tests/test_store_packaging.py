import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

MODULE = Path(__file__).resolve().parents[1] / 'packaging/microsoft_store/build_msix.py'
spec = importlib.util.spec_from_file_location('store_build', MODULE)
store_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store_build)


def test_unreserved_identity_cannot_create_submission():
    with pytest.raises(ValueError, match='製品ID'):
        store_build.read_identity()
    with pytest.raises(ValueError, match='identity_name'):
        store_build.read_identity(MODULE.parent / 'identity.example.json')


def test_preview_identity_cannot_be_reused_for_submission(tmp_path):
    path = tmp_path / 'identity.json'
    path.write_text(json.dumps(store_build.read_identity(development=True)), encoding='utf-8')
    with pytest.raises(ValueError, match='検証用'):
        store_build.read_identity(path)


def test_manifest_has_desktop_scope_no_network_and_escaped_publisher():
    identity = store_build.read_identity(development=True)
    identity['publisher_display_name'] = 'A & B'
    root = ET.fromstring(store_build.manifest(identity, '0.4.0'))
    ns = {'f': 'http://schemas.microsoft.com/appx/manifest/foundation/windows10'}
    assert root.find('f:Identity', ns).attrib['Version'] == '0.4.0.0'
    assert root.find('f:Properties/f:PublisherDisplayName', ns).text == 'A & B'
    assert root.find('f:Dependencies/f:TargetDeviceFamily', ns).attrib['Name'] == 'Windows.Desktop'
    assert root.find('f:Applications/f:Application', ns).attrib['Executable'] == 'SimpleAudioRecorder.exe'
    assert 'internetClient' not in store_build.manifest(identity, '0.4.0')
