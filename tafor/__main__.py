import os
import sys

import click

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tafor import conf, logger
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
    if name in ['sigmet', 'rpc']:
        path = 'General/{}'.format(name.capitalize())
        conf.setValue(path, True)
        logger.info('Install {}'.format(name))

@cli.command(help='Remove the specified function.')
@click.argument('name')
def remove(name):
    if name in ['sigmet', 'rpc']:
        path = 'General/{}'.format(name.capitalize())
        conf.setValue(path, False)
        logger.info('Remove {}'.format(name))

@cli.command(help='Run RPC server in debug mode.')
def runserver():
    from tafor.rpc import server
    server.run(debug=True, port=15400)


if __name__ == '__main__':
    cli()