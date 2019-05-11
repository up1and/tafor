import os
import sys

import click

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tafor import conf
from tafor.app.main import main

@click.group(invoke_without_command=True)
@click.option('--whysoserious', is_flag=True)
@click.pass_context
def cli(ctx, whysoserious):
    if ctx.invoked_subcommand is None:
        conf.setValue('General/Serious', whysoserious)
        main()

@cli.command(help='Install the specified function.')
@click.argument('name')
def install(name):
    if name == 'sigmet':
        path = 'General/{}'.format(name.capitalize())
        conf.setValue(path, True)

@cli.command(help='Remove the specified function.')
@click.argument('name')
def remove(name):
    if name == 'sigmet':
        path = 'General/{}'.format(name.capitalize())
        conf.setValue(path, False)


if __name__ == '__main__':
    cli()