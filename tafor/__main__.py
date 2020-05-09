import os
import sys
import secrets

import click

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tafor import conf, __version__
from tafor.app.main import main


def version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(__version__)
    ctx.exit()

@click.group(invoke_without_command=True)
@click.option('--whysoserious', is_flag=True)
@click.option('--version', is_flag=True, callback=version,
                expose_value=False, is_eager=True)
@click.pass_context
def cli(ctx, whysoserious):
    """Tafor is a terminal aerodrome forecast encoding software.

    Here you can enable some advanced features via the command line.

    Examples:\n
        tafor sigmet --enbale/--disable\n
        tafor token [--generate]

    Copyright:\n
    (c) 2019 up1and.
    """
    if ctx.invoked_subcommand is None:
        # It's a easter egg, but I haven't decided what to leave.
        conf.setValue('General/Serious', whysoserious)
        main()

@cli.command(help='Enable or disable SIGMET function.')
@click.option('--enbale/--disable')
def sigmet(enbale):
    path = 'General/Sigmet'
    if enbale:
        conf.setValue(path, True)
        click.echo('SIGMET function enabled')
    else:
        conf.setValue(path, False)
        click.echo('SIGMET function disabled')

@cli.command(help='Show or generate RPC token.')
@click.option('--generate', is_flag=True)
def token(generate):
    from tafor.states import context
    if generate:
        authToken = secrets.token_urlsafe(24)
        conf.setValue('AuthToken', authToken)
        click.echo(authToken)
    else:
        authToken = context.environ.token()
        click.echo(authToken)


if __name__ == '__main__':
    try:
        cli()
    except SystemError:
        # when package program without console, the click.echo function will raise error.
        pass
