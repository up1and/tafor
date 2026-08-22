import tafor.__main__ as cli


def test_no_command_launches_app(monkeypatch):
    launched = []

    monkeypatch.setattr(cli, 'main', lambda: launched.append(True))

    cli.cli([])

    assert launched == [True]


def test_version_prints_and_exits(capsys):
    try:
        cli.cli(['--version'])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError('Expected SystemExit for --version')

    assert capsys.readouterr().out.strip() == cli.__version__


def test_sigmet_enable(monkeypatch, capsys):
    conf = type('Conf', (), {'sigmetEnabled': False})()
    monkeypatch.setattr(cli, 'createConfig', lambda: conf)

    cli.cli(['sigmet', '--enable'])

    assert conf.sigmetEnabled is True
    assert capsys.readouterr().out.strip() == 'SIGMET support has been enabled.'


def test_sigmet_disable(monkeypatch, capsys):
    conf = type('Conf', (), {'sigmetEnabled': True})()
    monkeypatch.setattr(cli, 'createConfig', lambda: conf)

    cli.cli(['sigmet', '--disable'])

    assert conf.sigmetEnabled is False
    assert capsys.readouterr().out.strip() == 'SIGMET support has been disabled.'


def test_token_show(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'createConfig', lambda: type('Conf', (), {'authToken': 'current-token'})())

    cli.cli(['token'])

    assert 'current-token' in capsys.readouterr().out


def test_token_generate(monkeypatch, capsys):
    conf = type('Conf', (), {'authToken': 'old-token'})()

    monkeypatch.setattr(cli, 'createConfig', lambda: conf)
    monkeypatch.setattr(cli.secrets, 'token_urlsafe', lambda _: 'new-token')

    cli.cli(['token', '--generate'])

    assert conf.authToken == 'new-token'
    assert 'new-token' in capsys.readouterr().out
