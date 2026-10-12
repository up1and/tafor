"""Tests for the path, revision and app-info helpers in core.utils.common."""

import os
import sys

from tafor.core import root
from tafor.core.utils import common


def test_a_packaged_resource_is_resolved_under_the_resources_folder():
    path = common.resourcePath('icons/setting.png')

    assert path == os.path.join(root, 'resources') + os.sep + 'icons/setting.png'
    assert os.path.exists(path)


def test_icon_path_resolves_against_the_resources_icons_folder():
    path = common.iconPath('setting.png')

    assert path == os.path.join(root, 'resources', 'icons', 'setting.png')
    assert os.path.exists(path)


def test_a_missing_resource_falls_back_to_the_root_folder():
    # nothing to find under resources/, so the bare relative path is returned
    path = common.iconPath('no-such-icon.png')

    assert path == os.path.join(root, 'icons', 'no-such-icon.png')
    assert not os.path.exists(path)


def test_a_frozen_build_reads_resources_from_meipass(monkeypatch, tmp_path):
    icon = tmp_path / 'resources' / 'icons'
    icon.mkdir(parents=True)
    (icon / 'setting.png').write_bytes(b'x')
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)

    found = common.iconPath('setting.png')

    assert found == os.path.join(str(tmp_path), 'resources', 'icons', 'setting.png')
    assert os.path.exists(found)


def test_the_revision_is_a_string_when_running_from_a_checkout():
    assert isinstance(common.revision(), str)


def test_app_info_describes_the_running_environment():
    info = common.appInfo('5.15.11')

    assert info['qt'] == '5.15.11'
    assert info['python'] == sys.version.split()[0]
    assert info['system']
    assert info['machine']
    assert info['release']
    assert info['revision'] == common.revision()


def test_app_info_reports_an_empty_qt_when_none_is_given():
    assert common.appInfo()['qt'] == ''
