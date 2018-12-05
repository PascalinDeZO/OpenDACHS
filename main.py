#    OpenDACHS 1.0
#    Copyright (C) 2018  Carine Dengler, Heidelberg University
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
import argparse
import configparser
import logging

# third party imports
# library specific imports
import src.ticket_manager


def get_argument_parser():
    """Get argument parser.

    :returns: argument parser
    :rtype: ArgumentParser
    """
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("ftp", help="FTP configuration")
        parser.add_argument("smtp", help="SMTP configuration")
        parser.add_argument("sqlite", help="SQLite configuration")
    except Exception as exception:
        msg = "failed to get argument parser:{}".format(exception)
        raise SystemExit(msg)
    return parser


def read_config(filename):
    """Read INI configuration file in.

    :param str filename: configuration file filename

    :returns: config
    :rtype: ConfigParser
    """
    try:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(filename)
    except Exception as exception:
        msg = "failed to read INI configuration file {}in:{}".format(
            filename, exception
        )
        raise SystemExit(msg)
    return config


def main():
    """Main routine."""
    try:
        logging.basicConfig(
            filename="storage/opendachs.log",
            format="%(asctime) %(message)s",
            level=logging.INFO
        )
        parser = get_argument_parser()
        args = parser.parse_args()
        ftp = read_config(args.ftp)
        smtp = read_config(args.smtp)
        sqlite = read_config(args.sqlite)
        ticket_manager = src.ticket_manager.TicketManager(ftp, smtp, sqlite)
        ticket_manager.manage()
    except Exception as exception:
        msg = "an exception was raised:{}".format(exception)
        raise SystemExit(msg)
    return


if __name__ == "__main__":
    main()
