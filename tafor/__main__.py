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
@click.option('--version', is_flag=True, callback=version,
                expose_value=False, is_eager=True)
@click.pass_context
def cli(ctx):
    """Tafor is a terminal aerodrome forecast encoding software.

    Here you can enable some advanced features via the command line.

    Examples:\n
        tafor sigmet --enable/--disable\n
        tafor token [--generate]

    Copyright:\n
    (c) 2022 up1and.
    """
    if ctx.invoked_subcommand is None:
        main()

@cli.command(help='Enable or disable SIGMET function.')
@click.option('--enable/--disable')
def sigmet(enable):
    if enable:
        conf.sigmetEnabled = True
        click.echo('SIGMET function enabled')
    else:
        conf.sigmetEnabled = False
        click.echo('SIGMET function disabled')

@cli.command(help='Show or generate RPC token.')
@click.option('--generate', is_flag=True)
def token(generate):
    if generate:
        authToken = secrets.token_urlsafe(24)
        conf.authToken = authToken
        click.echo(authToken)
    else:
        click.echo(conf.authToken)


if __name__ == '__main__':
    try:
        cli()
    except SystemError:
        # when package program without console, the click.echo function will raise error.
        pass
