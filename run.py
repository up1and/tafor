import click

from tafor import setting
from tafor.app.main import main

@click.command()
@click.option('--debug', is_flag=True)
def cli(debug):
    setting.setValue('convention/debug', debug)
    main()

if __name__ == '__main__':
    cli()