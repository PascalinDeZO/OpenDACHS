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
    :ivar dict sql: SQLite queries
    :ivar list mails: e-mails
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
            self.sql = {"insert": [], "update": [], "delete": []}
            self.mails = []
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

    def _insert_ticket(self, file_):
        """Insert ticket.

        :param str file_: local file
        """
        try:
            logger = logging.getLogger().getChild(self._insert_ticket.__name__)
            dest = json.load(open(file_))
            timestamp = datetime.datetime.now()
            warc = self._write_warc(file_)
            parameters = (
                dest["ticket"],                     #: ticket
                dest["email"],                      #: e-mail address
                dest["url"],                        #: URL
                dest["creator"],                    #: creator(s)
                dest["title"],                      #: title
                dest["publisher"],                  #: publisher
                dest["publication_year"],           #: publication year
                dest["general_resource_type"],      #: general resource type
                dest["resource_type"],              #: resource type
                dest["flag"],                       #: flag
                timestamp,                          #: timestamp
                warc                                #: WARC filename
            )
            self.sql["insert"].append(parameters)
            self.mails.append(
                (dest["mail"], src.od_smtp.get_msg(self.smtp, file_))
            )
        except Exception:
            logger.exception("failed to insert ticket")
            raise
        return

    def _update_ticket(self, file_):
        """Update ticket.

        :param str file_: local file
        """
        raise NotImplementedError

    def _delete_ticket(self, file_):
        """Delete ticket.

        :param str file_: local file
        """
        raise NotImplementedError

    def process_ticket(self, file_):
        """Process ticket.

        :param str file_: local file
        """
        try:
            logger = logging.getLogger().getChild(self.process_ticket.__name__)
            dest = json.load(open(file_))
            if dest["flag"] == "pending":
                self._insert_ticket(file_)
            elif dest["flag"] == "confirmed" or dest["flag"] == "accepted":
                self._update_ticket(file_)
            elif dest["flag"] == "denied":
                self._delete_ticket(file_)
        except Exception:
            logger.exception("failed to process ticket %s", dest["ticket"])
            raise
        finally:
            os.unlink(file_)
        return

    def manage_tickets(self):
        """Manage tickets."""
        try:
            logger = logging.getLogger().getChild(
                self.manage_tickets.__name__
            )
            logger.info("manage tickets")
            logger.info("retrieve tickets")
            files = src.od_ftp.retrieve_files(self.ftp)
            logger.info("retrieved %d tickets", len(files))
            logger.info("process tickets")
            for file_ in files:
                try:
                    self._process_ticket(file_)
                except Exception:
                    logger.warning("failed to process ticket %s", file_)
            src.od_sqlite.execute(self.sqlite, self.sql)
            for k, v in self.sql.items():
                if k == "insert":
                    logger.info("inserted %d new tickets", len(v))
                elif k == "update":
                    logger.info("updated %d tickets", len(v))
                elif k == "delete":
                    logger.info("deleted %d tickets", len(v))
            src.od_smtp.sendmails(self.smtp, self.mails)
        except Exception:
            logger.exception("failed to prcocess files")
            raise
        return
