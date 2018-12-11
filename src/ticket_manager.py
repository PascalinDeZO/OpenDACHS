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
:synopsis: Ticket management.
"""


# standard library imports
import os
import re
import json
import base64
import shutil
import random
import string
import logging
import datetime
import collections
import subprocess

# third party imports

# library specific imports
import src.ftp
import src.email
import src.sqlite
import src.ticket
import src.scraper


class TicketManagerError(Exception):
    """Raised when ticket management fails."""
    pass


class TicketManager(object):
    """Ticket manager.

    :ivar ConfigParser ftp: FTP configuration
    :ivar ConfigParser smtp: SMTP configuration
    :ivar ConfigParser sqlite: SQLite configuration
    """

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
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            sqlite_client.create_table()
        except src.sqlite.SQLiteError:
            raise
        except Exception as exception:
            msg = "failed to initialize ticket manager"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception

    @staticmethod
    def generate_username(length=8):
        """Generate Webrecorder username.

        :param int length: length

        :returns: username
        :rtype: str
        """
        try:
            if length < 1:
                raise ValueError("length < 1")
            alphabet = string.ascii_letters + string.digits
            username = "".join(
                random.choice(alphabet) for _ in range(length)
            )
        except Exception as exception:
            msg = "failed to generate username"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return username

    @staticmethod
    def generate_password(length=16):
        """Generate Webrecorder password.

        Code snippet see
        https://stackoverflow.com/questions/3854692/generate-password-in-python

        :param int length: length

        :returns: password
        :rtype: str
        """
        # FIXME last two chars are always '99'
        try:
            if length < 1:
                raise ValueError("length < 1")
            alphabet = string.ascii_letters + string.digits
            password = "".join(
                alphabet[ord(char) % len(alphabet)]
                for char in base64.b64encode(os.urandom(length)).decode()
            )
        except Exception as exception:
            msg = "failed to generate password"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return password

    def archive(self, ticket):
        """Archive URL.

        Code snippet see https://github.com/webrecorder/warcio

        :param Ticket ticket: OpenDACHS ticket
        """
        try:
            scraper = src.scraper.Scraper(ticket)
            scraper.archive()
        except src.scraper.ScraperError:
            raise
        except Exception as exception:
            msg = "failed to archive {url}".format(url=ticket.metadata["url"])
            logging.exception(msg)
            raise TicketManagerError(msg) from exception

    @staticmethod
    def dump_ticket(ticket):
        """Dump OpenDACHS ticket.

        :param Ticket ticket: OpenDACHS ticket
        """
        try:
            json_file = "tmp/json_files/{}.json".format(ticket.id_)
            fp = open(json_file, mode="w")
            fp.write(ticket.get_json())
        except src.ticket.TicketError:
            raise
        except Exception as exception:
            msg = "failed to dump OpenDACHS ticket {id}".format(id=ticket.id_)
            logging.exception(msg)
            raise TicketManagerError(msg) from exception

    def _prettyprint(self, value, level=0):
        """Return prettyprint.

        :param value: value

        :returns: prettyprint
        :rtype: str
        """
        try:
            prettyprint = ""
            if type(value) == dict:
                for k, v in value.items():
                    v = self._prettyprint(v, level=level+1)
                    if v:
                        prettyprint += "{level}{k}:\n{v}".format(
                            level=level*"-",
                            k=k.title(),
                            v=v
                        )
            elif type(value) == list:
                for v in value:
                    v = self._prettyprint(v, level=level+1)
                    if v:
                        prettyprint += v
            elif type(value) == str:
                if value:
                    prettyprint += "{level}{v}\n".format(
                        level=level*"-", v=value
                    )
        except TicketManagerError:
            raise
        except Exception as exception:
            msg = "failed to return prettyprint"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return prettyprint

    def compose_plaintext_attachment(self, ticket):
        """Compose plaintext email attachment.

        :param Ticket ticket: OpenDACHS ticket

        :returns: plaintext attachment
        :rtype: MIMEText
        """
        try:
            filename = "info.txt"
            text = self._prettyprint(ticket.metadata)
            attachment = src.email.compose_attachment(filename, text)
        except TicketManagerError:
            raise
        except src.email.EmailError:
            raise
        except Exception as exception:
            msg = "failed to compose plaintext email attachment"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return attachment

    @staticmethod
    def compose_ris_attachment(ticket):
        """Compose RIS attachment.

        RIS file format see https://en.wikipedia.org/wiki/RIS_(file_format)

        :param Ticket ticket: OpenDACHS ticket

        :returns: RIS attachment
        :rtype: MIMEText
        """
        try:
            filename = "info.ris"
            text = ""
            tags = collections.OrderedDict(
                [
                    ("resourceType", "TY"),
                    ("creator", "A{}"),
                    ("publicationDate", "DA"),
                    ("subjectHeading", "KW"),
                    ("personHeading", "KW"),
                    ("publisher", "PB"),
                    ("title", "T{}"),
                    ("url", "UR")
                ]
            )
            field = "{tag}  - {value}\n"
            for key, tag in tags.items():
                if key == "creator":
                    for count, creator in enumerate(ticket.metadata[key]):
                        text += field.format(
                            tag=tag.format(count),
                            value=creator["romanization"]
                        )
                elif key == "publicationDate":
                    date = re.compile("([0-9]{4})([0-9]{2})([0-9]{2})")
                    match = date.match(ticket.metadata[key])
                    value = "{}/{}/{}".format(
                        match.group(1), match.group(2), match.group(3)
                    )
                    text += field.format(tag=tag, value=value)
                elif key == "subjectHeading" or key == "personHeading":
                    for keyword in ticket.metadata[key]:
                        if keyword:
                            text += field.format(tag=tag, value=keyword)
                elif key == "title":
                    text += field.format(
                        tag=tag.format(1),
                        value=ticket.metadata["title"]["romanization"]
                    )
                    if ticket.metadata["title"]["script"]:
                        text += field.format(
                            tag=tag.format(2),
                            value=ticket.metadata["title"]["script"]
                        )
                elif key == "publisher":
                    text += field.format(
                        tag=tag,
                        value=ticket.metadata[key]["romanization"]
                    )
                else:
                    text += field.format(
                        tag=tag, value=ticket.metadata[key]
                    )
            attachment = src.email.compose_attachment(filename, text)
        except src.email.EmailError:
            raise
        except Exception as exception:
            msg = "failed to compose RIS attachment"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return attachment

    def _initialize_user(self, data):
        """Initialize Webrecorder user.

        :param dict data: content of ticket file

        :returns: Webrecorder user
        :rtype: User
        """
        try:
            username = self.generate_username()
            role = "archivist"
            password = self.generate_password()
            email_addr = data["email"]
            user = src.ticket.User(username, role, password, email_addr)
        except TicketManagerError:
            raise
        except src.ticket.TicketError:
            raise
        except Exception as exception:
            msg = "failed to initialize Webrecorder user"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return user

    def _initialize_ticket(self, data):
        """Initialize OpenDACHS ticket.

        :param dict data: content of ticket file

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        try:
            id_ = data["ticket"]
            user = self._initialize_user(data)
            archive = "tmp/warcs/{}.warc".format(data["ticket"])
            metadata = {
                k: v for k, v in data.items()
                if k not in ["email", "ticket", "flag"]
            }
            flag = data["flag"]
            timestamp = datetime.datetime.now()
            ticket = src.ticket.Ticket(
                id_, user, archive, metadata, flag, timestamp
            )
        except TicketManagerError:
            raise
        except src.ticket.TicketError:
            raise
        except Exception as exception:
            msg = "failed to initialize OpenDACHS ticket"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return ticket

    def sendmail(self, ticket, name):
        """Send email.

        :param Ticket ticket: OpenDACHS ticket
        :param str name: name of email template
        """
        try:
            subject = "OpenDACHS Ticket {}".format(ticket.id_)
            if name == "submitted" or name == "confirmed":
                attachment = self.compose_plaintext_attachment(ticket)
                body = src.email.compose_body(
                    name,
                    ticket=ticket.id_,
                    username=ticket.user.username,
                    password=ticket.user.password
                )
            elif name in ["accepted", "denied", "expired"]:
                if name == "accepted":
                    attachment = self.compose_ris_attachment(ticket)
                body = src.email.compose_body(
                    name,
                    ticket=ticket.id_,
                    reply_to=self.smtp["header_fields"]["reply_to"]
                )
            elif name == "error":
                body = src.email.compose_body(name, ticket=ticket.id_)
            else:
                raise TicketManagerError(
                    "unknown email template {name}".format(name=name)
                )
            if name in ["submitted", "accepted", "denied", "expired"]:
                email_msg = src.email.compose_msg(
                    self.smtp, ticket.user.email_addr, subject, body,
                    attachment=locals().get("attachment")
                )
                src.email.sendmail(self.smtp, ticket.user.email_addr, email_msg)
            else:
                email_msg = src.email.compose_msg(
                    self.smtp,
                    self.smtp["header_fields"]["reply_to"],
                    subject,
                    body,
                    attachment=locals().get("attachment")
                )
                src.email.sendmail(
                    self.smtp, self.smtp["header_fields"]["reply_to"], email_msg
                )
        except TicketManagerError:
            raise
        except src.email.EmailError:
            raise
        except Exception as exception:
            msg = "failed to send email"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return

    def upload(self, src, dest):
        """Upload existing WARC archive.

        :param str src: source WARC archive file path
        :param str dest: destination WARC archive file path
        """
        raise NotImplementedError

    def submit(self, data):
        """Submit new OpenDACHS ticket.

        :param dict data: OpenDACHS ticket

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        try:
            ticket = self._initialize_ticket(data)
            if "warc" not in data:
                self.archive(ticket)
            else:
                self.upload(data["warc"], ticket.archive)
            row = ticket.get_row()
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            sqlite_client.insert([row])
            self.dump_ticket(ticket)
        except (
                src.scraper.ScraperError,
                src.sqlite.SQLiteError,
                src.ticket.TicketError,
                TicketManagerError
        ) as exception:
            msg = "failed to submit OpenDACHS ticket {ticket}".format(
                ticket=data["ticket"]
            )
            logging.warning(msg)
            raise TicketManagerError(msg) from exception
        except Exception as exception:
            msg = "failed to submit OpenDACHS ticket {ticket}".format(
                ticket=data["ticket"]
            )
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return ticket

    def confirm(self, data):
        """Confirm ticket.

        :param dict data: OpenDACHS ticket

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        try:
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.update_row(
                "flag", "ticket", (data["flag"], data["ticket"])
            )
            ticket = src.ticket.Ticket.get_ticket(row)
        except (src.sqlite.SQLiteError, src.ticket.TicketError) as exception:
            msg = "failed to confirm OpenDACHS ticket {ticket}".format(
                ticket=data["ticket"]
            )
            logging.warning(msg)
            raise TicketManagerError(msg) from exception
        except Exception as exception:
            msg = "failed to confirm OpenDACHS ticket {ticket}".format(
                ticket=data["ticket"]
            )
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return ticket

    def accept(self, data):
        """Accept ticket.

        :param dict data: OpenDACHS ticket

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        try:
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.select_row("ticket", (data["ticket"],))
            ticket = src.ticket.Ticket.get_ticket(row)
            storage = "storage/{ticket}".format(ticket=data["ticket"])
            path = "./../webrecorder/data/warcs/{user}".format(
                user=ticket.user.username
            )
            if os.access(path, os.F_OK):
                shutil.copytree(path, storage)
            else:
                os.makedirs(storage, exist_ok=True)
                shutil.copyfile(
                    ticket.archive, storage+"/{}.warc".format(ticket.id_)
                )
            os.unlink(ticket.archive)
            logging.info("moved WARC %s to storage", ticket.archive)
            sqlite_client.delete("ticket", [(ticket.id_,)])
            logging.info("deleted ticket %s", ticket.id_)
            ticket.flag = "deleted"
            self.dump_ticket(ticket)
        except (
            src.sqlite.SQLiteError,
            src.ticket.TicketError,
            TicketManagerError
        ) as exception:
            msg = "failed to accept OpenDACHS ticket {ticket}".format(
                ticket=data["ticket"]
            )
            logging.warning(msg)
            raise TicketManagerError(msg) from exception
        except Exception as exception:
            msg = "failed to accept OpenDACHS ticket {ticket}".format(
                ticket = data["ticket"]
            )
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return ticket

    def deny(self, data):
        """Deny ticket.

        :param dict data: OpenDACHS ticket

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        try:
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.select_row("ticket", (data["ticket"],))
            ticket = src.ticket.Ticket.get_ticket(row)
            os.unlink(ticket.archive)
            sqlite_client.delete("ticket", [(ticket.id_,)])
            ticket.flag = "deleted"
            self.dump_ticket(ticket)
        except (
                src.sqlite.SQLiteError,
                src.ticket.TicketError,
                TicketManagerError
        ) as exception:
            msg = "failed to deny OpenDACHS ticket {ticket}".format(
                ticket=data["ticket"]
            )
            logging.warning(msg)
            raise TicketManagerError(msg) from exception
        except Exception as exception:
            msg = "failed to deny OpenDACHS ticket {ticket}".format(
                ticket=data["ticket"]
            )
            logging.exception(msg)
            raise TicketManagerError(msg) from exception
        return ticket

    def remove_expired(self):
        """Remove expired OpenDACHS tickets."""
        try:
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            parameters = (
                datetime.datetime.now() - datetime.timedelta(days=3),
            )
            rows = sqlite_client.select_rows(
                column="timestamp",
                parameters=parameters,
                operator="<"
            )
            tickets = [src.ticket.Ticket.get_ticket(row) for row in rows]
            for ticket in tickets:
                try:
                    if ticket.flag == "pending":
                        logging.info(
                            "remove expired ticket %s (timestamp %s)",
                            ticket.id_, ticket.timestamp
                        )
                        os.unlink(ticket.archive)
                        sqlite_client.delete("ticket", [(ticket.id_,)])
                        ticket.flag = "deleted"
                        self.dump_ticket(ticket)
                        yield(ticket)
                except (
                        src.sqlite.SQLiteError,
                        src.ticket.TicketError,
                        TicketManagerError
                ) as exception:
                    msg = "failed to remove OpenDACHS ticket {ticket}".format(
                        ticket=ticket.id_
                    )
                    logging.warning(msg)
                    raise TicketManagerError(msg) from exception
                except Exception as exception:
                    msg = "failed to remove OpenDACHS ticket {ticket}".format(
                        ticket=ticket.id_
                    )
                    logging.exception(msg)
                    raise TicketManagerError(msg) from exception
        except (
                src.sqlite.SQLiteError,
                src.ticket.TicketError,
                TicketManagerError
        ) as exception:
            msg = "failed to remove one or more expired OpenDACHS tickets"
            logging.warning(msg)
            raise TicketManagerError(msg) from exception
        except Exception as exception:
            msg = "failed to remove one or more expired OpenDACHS tickets"
            logging.exception(msg)
            raise TicketManagerError(msg) from exception

    def call_api(self):
        """Call Webrecorder API."""
        # FIXME stdout is not logged
        try:
            args = [
                "docker", "exec", "-it", "webrecorder_app_1",
                "python3", "-m", "webrecorder.opendachs"
            ]
            child = subprocess.Popen(args, stderr=subprocess.PIPE)
            while True:
                returncode = child.poll()
                if returncode is None:
                    continue
                else:
                    break
            if child.returncode != 0:
                msg = "failed to call Webrecorder API (exit status {})".format(
                    child.returncode
                )
                logging.exception(msg)
                raise TicketManagerError(msg)
        except TicketManagerError:
            raise
        except Exception as exception:
            msg = "failed to call Webrecorder API"
            logging.exception(msg)
            raise TicketManagerError(msg)

    def manage(self):
        """Manage OpenDACHS tickets."""
        logger = logging.getLogger().getChild(self.manage.__name__)
        logger.info("retrieve ticket files")
        files = src.ftp.retrieve_files(self.ftp)
        logger.info("retrieved %d tickets", len(files))
        counter = {
            "submitted": 0,
            "confirmed": 0,
            "accepted": 0,
            "denied": 0,
            "removed": 0
        }
        for filename in files:
            with open(filename) as fp:
                data = json.load(fp)
            try:
                flag = data["flag"]
                if flag == "pending":
                    ticket = self.submit(data)
                    flag = "submitted"
                elif flag == "confirmed":
                    ticket = self.confirm(data)
                elif flag == "accepted":
                    ticket = self.accept(data)
                elif flag == "denied":
                    ticket = self.deny(data)
                else:
                    raise TicketManagerError(
                        "unknown flag {flag}".format(flag=flag)
                    )
            except TicketManagerError:
                if "ticket" not in locals():
                    ticket = src.ticket.Ticket(data["ticket"], *(5*(None,)))
                self.sendmail(ticket, "error")
                raise
            except Exception as exception:
                if "ticket" not in locals():
                    ticket = src.ticket.Ticket(data["ticket"], *(5*(None,)))
                msg = "failed to manage OpenDACHS ticket {ticket}".format(
                    ticket=ticket.id_
                )
                logging.exception(msg)
                self.sendmail(ticket, "error")
                raise TicketManagerError(msg)
            try:
                self.call_api()
                self.sendmail(ticket, flag)
                counter[flag] += 1
            except TicketManagerError:
                msg = "failed to complete OpenDACHS ticket {ticket}".format(
                    ticket=ticket.id_
                )
                logging.warning(msg)
                self.sendmail(ticket, "error")
                raise
            except Exception as exception:
                msg = "failed to complete OpenDACHS ticket {ticket}".format(
                    ticket=ticket.id_
                )
                logging.exception(msg)
                self.sendmail(ticket, "error")
        for ticket in self.remove_expired():
            try:
                self.call_api()
                counter["removed"] += 1
                self.sendmail(ticket, "expired")
            except TicketManagerError:
                self.sendmail(ticket, "error")
                raise
            except Exception as exception:
                msg = (
                    "failed to remove expired OpenDACHS ticket {ticket}".format(
                        ticket=ticket.id_
                    )
                )
                logging.exception(msg)
                self.sendmail(ticket, "error")
                raise TicketManagerError(msg)
        for key, value in counter.items():
            logging.info("%s %d tickets", key, value)
        return