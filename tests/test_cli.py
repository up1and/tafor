import tafor.__main__ as cli


def test_no_command_launches_app(monkeypatch):
    launched = []

    monkeypatch.setattr('tafor.app.main.main', lambda: launched.append(True))

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
    monkeypatch.setattr(cli, 'conf', type('Conf', (), {'sigmetEnabled': False})())

    cli.cli(['sigmet', '--enable'])

    assert cli.conf.sigmetEnabled is True
    assert capsys.readouterr().out.strip() == 'SIGMET function enabled'


def test_sigmet_default_disables(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'conf', type('Conf', (), {'sigmetEnabled': True})())

    cli.cli(['sigmet'])

    assert cli.conf.sigmetEnabled is False
    assert capsys.readouterr().out.strip() == 'SIGMET function disabled'


def test_token_show(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'conf', type('Conf', (), {'authToken': 'current-token'})())

    cli.cli(['token'])

    assert capsys.readouterr().out.strip() == 'current-token'


def test_token_generate(monkeypatch, capsys):
    conf = type('Conf', (), {'authToken': 'old-token'})()

    monkeypatch.setattr(cli, 'conf', conf)
    monkeypatch.setattr(cli.secrets, 'token_urlsafe', lambda _: 'new-token')

    cli.cli(['token', '--generate'])

    assert conf.authToken == 'new-token'
    assert capsys.readouterr().out.strip() == 'new-token'
