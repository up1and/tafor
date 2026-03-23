import argparse
import os
import secrets
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tafor import conf, context, __version__
from tafor.ui import main


EPILOG = """Examples:
  tafor sigmet --enable/disable
  tafor token [--generate]

Copyright:
  (c) 2022 up1and.
"""


def build_parser():
    parser = argparse.ArgumentParser(
        prog='tafor',
        description='Tafor is a terminal aerodrome forecast encoding software.',
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--version', action='version', version=__version__)

    subparsers = parser.add_subparsers(dest='command')

    sigmet_parser = subparsers.add_parser(
        'sigmet',
        help='Enable or disable SIGMET support.',
        description='Enable or disable SIGMET support in the application configuration.',
    )
    sigmet_group = sigmet_parser.add_mutually_exclusive_group(required=True)
    sigmet_group.add_argument('--enable', dest='enable', action='store_true', help='Enable SIGMET support.')
    sigmet_group.add_argument('--disable', dest='enable', action='store_false', help='Disable SIGMET support.')

    token_parser = subparsers.add_parser(
        'token',
        help='Show or generate the RPC token.',
        description='Show the current RPC auth token, or generate a new one.',
    )
    token_parser.add_argument('--generate', action='store_true', help='Generate and save a new RPC auth token.')

    return parser


def cli(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        return main(conf, context)

    if args.command == 'sigmet':
        conf.sigmetEnabled = args.enable
        if args.enable:
            print('SIGMET support has been enabled.')
        else:
            print('SIGMET support has been disabled.')
        return

    if args.command == 'token':
        if args.generate:
            conf.authToken = secrets.token_urlsafe(24)
            print('A new RPC auth token has been generated and saved:')
            print(conf.authToken)
        else:
            print('Current RPC auth token:')
            print(conf.authToken)
        return


if __name__ == '__main__':
    try:
        sys.exit(cli())
    except (SystemError, BrokenPipeError, AttributeError):
        # When packaged without a console, stdout access may raise SystemError.
        pass
