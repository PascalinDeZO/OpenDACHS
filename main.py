#    OpenDACHS 1.0
#    Copyright (C) 2018  Carine Dengler
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
:synopsis: OpenDACHS.
"""


# standard library imports
import logging
import argparse
import configparser

# third party imports
# library specific imports
import src.od_ticket_manager


def get_argument_parser():
    """Get argument parser.

    :returns: argument parser
    :rtype: ArgumentParser
    """
    try:
        logger = logging.getLogger(get_argument_parser.__name__)
        parser = argparse.ArgumentParser()
        parser.add_argument("ftp", help="FTP configuration")
        parser.add_argument("smtp", help="SMTP configuration")
        parser.add_argument("sqlite", help="SQLite configuration")
    except Exception:
        logger.exception("failed to get argument parser")
        raise
    return parser


def read_config(file_):
    """Read INI configuration file in.

    :param str file_: configuration file name

    :returns: config
    :rtype: ConfigParser
    """
    try:
        logger = logging.getLogger(read_config.__name__)
        config = configparser.ConfigParser()
        config.read(file_)
    except Exception:
        logger.exception("failed to read configuration file %s in", file_)
        raise SystemExit
    return config


def main():
    """main routine."""
    try:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(main.__name__)
        parser = get_argument_parser()
        args = parser.parse_args()
        ftp = read_config(args.ftp)
        smtp = read_config(args.smtp)
        sqlite = read_config(args.sqlite)
        ticket_manager = src.od_ticket_manager.TicketManager(ftp, smtp, sqlite)
        ticket_manager.process_tickets()
    except Exception:
        logger.exception("an exception was raised")
        raise SystemExit
    return


if __name__ == "__main__":
    main()
