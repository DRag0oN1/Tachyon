"""Private filesystem launch handoff; never an unauthenticated token API."""
import json
import logging
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from tachyon.app import create_app
from tachyon.config import Settings
from tachyon.errors import TachyonError
from tachyon.launch import descriptor_path, read_owner_launch, write_owner_launch, open_owner_launch

@pytest.fixture
def settings(tmp_path):
    return Settings(root=tmp_path, data_dir=tmp_path/'private', ui_origin='http://127.0.0.1:8019')


def test_handoff_is_private_and_not_available_over_http(settings,caplog):
    caplog.set_level(logging.INFO,logger='uvicorn.error')
    with TestClient(create_app(settings)) as client:
        token=client.app.state.session;path=descriptor_path(settings)
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700
        assert read_owner_launch(settings)==(settings.ui_origin,token)
        assert token not in caplog.text
        assert client.get('/api/workspace').status_code==401
        assert client.get('/api/session').status_code==401
        assert client.get('/runtime/owner-launch-8019.json').status_code==404
        assert token not in client.get('/api/health').text
    assert not path.exists()


def test_restart_rotates_credentials_and_retains_workspace(settings):
    with TestClient(create_app(settings)) as first:
        old=first.app.state.session
        first.patch('/api/workspace',headers={'X-Tachyon-Session':old,'Origin':settings.ui_origin},json={'preferences':{'theme':'shift'}})
    with TestClient(create_app(settings)) as second:
        new=second.app.state.session
        assert new!=old and read_owner_launch(settings)[1]==new
        assert second.get('/api/workspace',headers={'X-Tachyon-Session':old}).status_code==401
        assert second.get('/api/workspace',headers={'X-Tachyon-Session':new}).json()['preferences']['theme']=='shift'


def test_launcher_checks_current_server_before_opening(settings,monkeypatch):
    import httpx,webbrowser
    write_owner_launch(settings,'owner-unit-token')
    fetch=Mock(return_value=Mock(status_code=200));opening=Mock(return_value=True)
    monkeypatch.setattr(httpx,'get',fetch);monkeypatch.setattr(webbrowser,'open',opening)
    assert open_owner_launch(settings,port=8019) is None
    opening.assert_called_once_with(settings.ui_origin+'/#session=owner-unit-token')
    assert fetch.call_args.kwargs['follow_redirects'] is False
    assert fetch.call_args.kwargs['trust_env'] is False
    opening.reset_mock()
    assert open_owner_launch(settings,port=8019,show_url=True).endswith('#session=owner-unit-token')
    opening.assert_not_called()
    fetch.return_value.status_code=401
    with pytest.raises(TachyonError,match='no longer authorized'):open_owner_launch(settings,port=8019)
    opening.assert_not_called()


@pytest.mark.parametrize('origin',['https://example.com','http://192.168.1.5:8019','http://127.0.0.1:8019/anything','http://user@127.0.0.1:8019','http://127.0.0.1:8019/?x=1'])
def test_tampered_handoff_cannot_send_credentials_to_other_hosts(settings,origin):
    path=write_owner_launch(settings,'owner-unit-token');data=json.loads(path.read_text());data['origin']=origin;path.write_text(json.dumps(data))
    with pytest.raises(TachyonError):read_owner_launch(settings,8019)


def test_symlinks_and_publicly_readable_handoff_are_refused(settings,tmp_path):
    target=tmp_path/'unrelated';target.write_text('preserved')
    path=descriptor_path(settings);path.parent.mkdir(parents=True);path.symlink_to(target)
    with pytest.raises(TachyonError):write_owner_launch(settings,'owner-unit-token')
    assert target.read_text()=='preserved'
    path.unlink();write_owner_launch(settings,'owner-unit-token');os.chmod(path,0o644)
    with pytest.raises(TachyonError):read_owner_launch(settings,8019)


def test_fresh_terminal_discovers_server_independently_of_its_private_cad_profile(settings):
    write_owner_launch(settings,'owner-unit-token')
    fresh=Settings(root=settings.root,data_dir=settings.root/'.local',ui_origin='http://127.0.0.1:8000')
    assert read_owner_launch(fresh,port=8019)==(settings.ui_origin,'owner-unit-token')
