import os
import sys

import click

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tafor import setting
from tafor.app.main import main

@click.command()
@click.option('--debug', is_flag=True)
def cli(debug):
    setting.setValue('convention/debug', debug)
    main()

if __name__ == '__main__':
    cli()