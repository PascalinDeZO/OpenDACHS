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
:synopsis: Ticket management.
"""


# standard library imports
import io
import os
import json
import logging
import datetime

# third party imports
import requests
import warcio

# library specific imports
import src.od_ftp
import src.od_smtp
import src.od_sqlite


class TicketManager(object):
    """Ticket manager.

    :cvar str DIR: output directory
    :cvar str LOCAL_FILES_DIR: local files output directory
    :cvar str WARCS_DIR: WARCs output directory

    :ivar ConfigParser ftp: FTP configuration
    :ivar ConfigParser smtp: SMTP configuration
    :ivar ConfigParser sqlite: SQLite configuration
    """
    DIR = "tmp"
    WARCS_DIR = "{}/warc".format(DIR)

    def __init__(self, ftp, smtp, sqlite):
        """Initialize ticket management.

        :param ConfigParser ftp: FTP configuration
        :param ConfigParser smtp: SMTP configuration
        :param ConfigParser sqlite: SQLite configuration
        """
        try:
            self.ftp = ftp
            self.smtp = smtp
            self.sqlite = sqlite
            src.od_sqlite.create_table(self.sqlite)
            os.makedirs(self.WARCS_DIR, exist_ok=True)
        except Exception:
            raise
        return

    def _write_warc(self, file_):
        """Write WARC.

        :param str file_: local file

        :returns: WARC filename
        :rtype: str
        """
        try:
            logger = logging.getLogger().getChild(self._write_warc.__name__)
            dest = json.load(open(file_))
            warc = "{}/{}.warc".format(self.WARCS_DIR, dest["ticket"])
            fp = open(warc, mode="wb")
            writer = warcio.warcwriter.WARCWriter(fp, gzip=True)
            logger.info("send GET request {}".format(dest["url"]))
            response = requests.get(dest["url"])
            if response.status_code != 200:
                raise RuntimeError(
                    "{}:\tHTTP status code {}".format(
                        dest["url"], response.status_code
                    )
                )
            else:
                headers = response.raw.headers.items()
                status_line = "200 OK"
                protocol = "HTTP/1.x"
                status_and_headers = warcio.statusandheaders.StatusAndHeaders(
                    status_line, headers, protocol=protocol
                )
                warc_record = writer.create_warc_record(
                    dest["url"],
                    "response",
                    payload=io.BytesIO(response.content),
                    http_headers=status_and_headers
                )
                writer.write_record(warc_record)
        except Exception:
            logger.exception("failed to write WARC %s", dest["ticket"])
            raise
        return warc

    def process_ticket(self, file_):
        """Process ticket.

        :param str file_: local file

        :returns: row
        :rtype: tuple
        """
        try:
            logger = logging.getLogger().getChild(self.process_ticket.__name__)
            dest = json.load(open(file_))
            timestamp = datetime.datetime.now()
            warc = self._write_warc(file_)
            row = (
                dest["ticket"],
                dest["email"],
                dest["url"],
                dest["creator0"],
                dest["title"],
                dest["publisher"],
                dest["publicationYear"],
                dest["generalResourceType"],
                dest["resourceType"],
                dest["flag"],
                timestamp,
                warc
            )
            mail = (dest["email"], src.od_smtp.get_msg(self.smtp, file_))
        except Exception:
            logger.exception("failed to process ticket %s", dest["ticket"])
            raise
        finally:
            os.unlink(file_)
        return row, mail

    def process_tickets(self):
        """Process tickets."""
        try:
            logger = logging.getLogger().getChild(
                self.process_tickets.__name__
            )
            logger.info("retrieve files")
            files = src.od_ftp.retrieve_files(self.ftp)
            logger.info("process tickets")
            rows = []
            mails = []
            for file_ in files:
                try:
                    row, mail = self.process_ticket(file_)
                    rows.append(row)
                    mails.append(mail)
                except Exception:
                    logger.warning("failed to process ticket")
                    raise
            src.od_sqlite.insert_rows(self.sqlite, rows)
            src.od_smtp.sendmails(self.smtp, mails)
        except Exception:
            logger.exception("failed to process tickets")
            raise
        return
