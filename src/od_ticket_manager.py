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
import ftplib
import logging
import sqlite3
import datetime

# third party imports
import requests

import warcio

# library specific imports


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
    LOCAL_FILES_DIR = "{}/json".format(DIR)
    WARCS_DIR = "{}/warc".format(DIR)

    def __init__(self, ftp, smtp, sqlite):
        """Initialize ticket manager.

        :param ConfigParser ftp: FTP configuration
        :param ConfigParser smtp: SMTP configuration
        :param ConfigParser sqlite: SQLite configuration
        """
        try:
            self.ftp = ftp
            self.smtp = smtp
            self.sqlite = sqlite
            self._create_table()
        except Exception:
            raise
        return

    def _create_table(self):
        """Create table if not exists."""
        try:
            logger = logging.getLogger.getChild(self._create_table.__name__)
            connection = sqlite3.connect(
                self.sqlite["SQLITE"]["database"],
                detect_types=sqlite3.PARSE_COLNAMES
            )
            sql = (
                "CREATE TABLE IF NOT EXISTS ?",
                "(? STRING PRIMARY KEY,",
                "? EMAIL, ? TIMESTAMP, ? STRING, ? STRING)"
            )
            connection.execute(
                sql, "tickets", "ticket", "email", "timestamp", "json", "warc"
            )
            connection.commit()
            connection.close()
        except Exception:
            logger.exception("failed to create table")
            raise SystemExit
        return

    def _get_ftp_client(self):
        """Get FTP client.

        :returns: FTP client
        :rtype: FTP_TLS
        """
        try:
            logger = logging.getLogger().getChild(
                self._get_ftp_client.__name__
            )
            ftp_client = ftplib.FTP_TLS(**self.ftp["FTP"])
        except KeyError:
            logger.exception("'FTP' header required")
            raise
        except Exception:
            logger.exception("failed to get FTP client")
            raise
        return ftp_client

    def retrieve_file(self, ftp_client, file_):
        """Retrieve file.

        :param FTP_TLS ftp_client: FTP client
        :param str file_: filename

        :returns: local filename
        :rtype: str
        """
        try:
            logger = logging.getLogger().getChild(self.retrieve_file.__name__)
            local_file = "{}/{}".format(self.LOCAL_FILES_DIR, file_)
            fp = open(local_file)
            ftp_client.retrbinary("RETR {}".format(file_), fp.write)
            ftp_client.delete(file_)
        except Exception:
            logger.exception("failed to retrieve file %s", file_)
            raise
        return local_file

    def retrieve_files(self):
        """Retrieve files.

        :returns: local filenames
        :rtype: list
        """
        try:
            logger = logging.getLogger().getChild(self.retrieve_files.__name__)
            ftp_client = self._get_ftp_client()
            local_files = []
            os.makedirs(self.LOCAL_FILES_DIR, exist_ok=True)
            for file_ in ftp_client.mlsd(self.ftp["cmd"]["RETR"]):
                local_files.append(self.retrieve_file(ftp_client, file_))
        except KeyError:
            logger.exception("'cmd' header required")
            raise
        except Exception:
            logger.exception("failed to retrieve files")
            raise
        return local_files

    def write_warc(self, file_):
        """Write WARC.

        :param str file_: local filename

        :returns: WARC filename
        :rtype: str
        """
        try:
            logger = logging.getLogger().getChild(self.write_warc.__name__)
            dest = json.load(open(file_))
            warc = "{}/{}.warc".format(self.WARCS_DIR, dest["ticket"])
            fp = open(warc, "wb")
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
            logger.exception("an exception was raised during writing of WARC")
            raise
        return warc

    def write_warcs(self, files):
        """Write WARCs.

        :param list files: local filenames

        :returns: WARC filenames
        :rtype: list
        """
        try:
            logger = logging.getLogger().getChild(self.write_warcs.__name__)
            os.makedirs(self.WARCS_DIR, exist_ok=True)
            warcs = []
            for file_ in files:
                warcs.append((file_, self.write_warc(file_)))
        except Exception:
            logger.exception("failed to write WARCs")
            raise
        return warcs

    def _get_rows(self, warcs):
        """Get rows.

        :param list warcs: WARC filenames

        :returns: rows
        :rtype: list
        """
        try:
            logger = logging.getLogger().getChild(self._get_rows.__name__)
            rows = []
            for file_, warc in warcs:
                dest = json.load(open(file_))
                rows.append(
                    [
                        dest["ticket"],
                        dest["email"],
                        datetime.datetime.now(),
                        file_,
                        warc
                    ]
                )
        except Exception:
            logger.exception("failed to get rows")
            raise
        return rows

    def _insert_rows(self, rows):
        """Insert rows.

        :param list rows: rows
        """
        try:
            logger = logging.getLogger().getChild(self._insert_rows.__name__)
            connection = sqlite3.connect(
                self.sqlite["SQLITE"]["database"],
                detect_types=sqlite3.PARSE_COLNAMES
            )
            sql = ("INSERT INTO tickets VALUES (?, ?, ?, ?, ?)")
            connection.executemany(sql, rows)
            connection.commit()
            connection.close()
        except Exception:
            logger.exception("failed to insert rows")
            raise
        return

    def process_tickets(self):
        """Process tickets."""
        try:
            logger = logging.getLogger().getChild(
                self.process_tickets.__name__
            )
            logger.info("process tickets")
            msg = "STAGE %d\t: %s"
            stage = 1
            logger.info(msg, stage, "retrieving tickets")
            stage += 1
            files = self.retrieve_files()
            logger.info(msg, stage, "writing WARCs")
            stage += 1
            warcs = self.write_warcs(files)
            logger.info(msg, stage, "inserting tickets")
            stage += 1
            rows = self._get_rows(warcs)
            self._insert_rows(rows)
            logger.info(msg, stage, "sending mails")
        except Exception:
            logger.exception("failed to process tickets")
            raise
        return
