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
    :ivar SQLiteClient sqlite_client: OpenDACHS SQLite database client
    :ivar dict queue: ticket queue
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
            logger = logging.getLogger().getChild(self.__init__.__name__)
            self.ftp = ftp
            self.smtp = smtp
            self.sqlite_client = src.od_sqlite.SQLiteClient(sqlite)
            self.queue = {
                "submit": [], "confirm": [], "accept": [], "deny": []
            }
            self.sqlite_client.create_table()
            os.makedirs(self.WARCS_DIR, exist_ok=True)
        except Exception:
            logger.exception("failed to initialize ticket management")
            raise
        return

    def write_warc(self, file_):
        """Write WARC.

        :param str file_: local file

        :returns: WARC filename
        :rtype: str
        """
        try:
            logger = logging.getLogger().getChild(self.write_warc.__name__)
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

    def submit_ticket(self, file_):
        """Submit ticket.

        :param str file_: local file
        """
        try:
            logger = logging.getLogger().getChild(self.submit_ticket.__name__)
            dest = json.load(open(file_))
            parameters = []
            for k in self.sqlite_client.sqlite["column_defs"].keys():
                if k not in ["timestamp", "warc"]:
                    if k == "creator":
                        parameters.append(json.dumps(dest[k]))
                    else:
                        parameters.append(dest[k])
                elif k == "timestamp":
                    parameters.append(datetime.datetime.now())
                elif k == "warc":
                    parameters.append(self.write_warc(file_))
            parameters = tuple(parameters)
            mail = (dest["email"], src.od_smtp.get_msg(self.smtp, file_))
            self.queue["submit"].append((mail, parameters))
        except Exception:
            logger.exception("failed to submit ticket")
            raise
        return

    def manage_ticket(self, file_):
        """Manage ticket.

        :param str file_: local file
        """
        try:
            logger = logging.getLogger().getChild(self.manage_ticket.__name__)
            dest = json.load(open(file_))
            if dest["flag"] == "pending":
                self.submit_ticket(file_)
        except Exception:
            logger.exception("failed to manage ticket %s", dest["ticket"])
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
                    self.manage_ticket(file_)
                except Exception as exception:
                    logger.warning("failed to manage ticket\t: %s", exception)
            self.sqlite_client.insert(
                [record for _, record in self.queue["submit"]]
            )
            src.od_smtp.sendmails(
                self.smtp, [mail for mail, _ in self.queue["submit"]]
            )
            for k, v in self.queue.items():
                if k == "submit":
                    logger.info("submitted %d new tickets", len(v))
                elif k == "confirm":
                    logger.info("confirmed %d tickets", len(v))
                elif k == "accept":
                    logger.info("accepted %d tickets", len(v))
                elif k == "deny":
                    logger.info("denied %d tickets", len(v))
        except Exception:
            logger.exception("failed to prcocess files")
            raise
        return
