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
import io
import os
import re
import json
import base64
import random
import string
import logging
import datetime
import collections

# third party imports
import bs4
import warcio.capture_http
import cfscrape

# library specific imports
import src.ftp
import src.email
import src.sqlite
import src.ticket


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
        :param ConfigParser sqlite SQLite configuration
        """
        try:
            self.ftp = ftp
            self.smtp = smtp
            self.sqlite = sqlite
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            sqlite_client.create_table()
        except Exception as exception:
            msg = "failed to initialize ticket manager:{}".format(exception)
            raise RuntimeError(msg)
        return

    @staticmethod
    def generate_username(length=8):
        """Generate Webrecorder username.

        :param int length: length

        :returns: username
        :rtype: str
        """
        try:
            alphabet = string.ascii_letters + string.digits
            username = "".join(
                random.choice(alphabet) for _ in range(length)
            )
        except Exception as exception:
            msg = "failed to generate username:{}".format(exception)
            raise RuntimeError(msg)
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
        try:
            alphabet = string.ascii_letters + string.digits
            password = "".join(
                alphabet[ord(char) % len(alphabet)]
                for char in base64.b64encode(os.urandom(length)).decode()
            )
        except Exception as exception:
            msg = "failed to generate password:{}".format(exception)
            raise RuntimeError(msg)
        return password

    @staticmethod
    def _archive_images(response):
        """Archive images.

        :param Response response: response
        """
        try:
            scraper = cfscrape.create_scraper()
            soup = bs4.BeautifulSoup(response.content)
            for img in soup.find_all("img"):
                yield scraper.get(img.src)
        except Exception as exception:
            msg = "failed to archive image: {}".format(exception)
            raise RuntimeError(msg)

    def archive(self, ticket):
        """Archive URL.

        Code snippet see https://github.com/webrecorder/warcio

        :param Ticket ticket: OpenDACHS ticket
        """
        try:
            scraper = cfscrape.create_scraper()
            with warcio.capture_http.capture_http(ticket.archive):
                response = scraper.get(ticket.metadata["url"])
                self._archive_images(response)
        except RuntimeError:
            raise
        except Exception as exception:
            msg = "failed to archive {}:{}".format(
                ticket.metadata["url"], exception
            )
            raise RuntimeError(msg)
        return

    @staticmethod
    def dump_ticket(ticket):
        """Dump OpenDACHS ticket.

        :param Ticket ticket: OpenDACHS ticket
        """
        try:
            json_file = "tmp/json_files/{}.json".format(ticket.id_)
            fp = open(json_file, mode="w")
            fp.write(ticket.get_json())
        except Exception as exception:
            msg = "failed to dump OpenDACHS ticket {}:{}".format(
                ticket.id_, exception
            )
            raise RuntimeError(msg)
        return

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
        except Exception as exception:
            msg = "failed to return prettyprint:{}".format(exception)
            raise RuntimeError(msg)
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
        except Exception as exception:
            msg = "failed to compose plaintext email attachment:{}".format(
                exception
            )
            raise RuntimeError(msg)
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
                        value = ticket.metadata[key]["romanization"]
                    )
                else:
                    text += field.format(
                        tag=tag, value=ticket.metadata[key]
                    )
            attachment = src.email.compose_attachment(filename, text)
        except Exception as exception:
            msg = "failed to compose RIS attachment:{}".format(exception)
            raise RuntimeError(msg)
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
        except Exception as exception:
            msg = "failed to initialize user:{}".format(exception)
            raise RuntimeError(msg)
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
        except Exception as exception:
            msg = "failed to initialize OpenDACHS ticket:{}".format(exception)
            raise RuntimeError(msg)
        return ticket

    def sendmail(self, ticket, name):
        """Send email.

        :param Ticket ticket: OpenDACHS ticket
        :param str name: name of email template
        """
        try:
            subject = "OpenDACHS Ticket {}".format(ticket.user.username)
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
            email_msg = src.email.compose_msg(
                self.smtp, ticket.user.email_addr, subject, body,
                attachment=locals().get("attachment")
            )
            src.email.sendmail(self.smtp, ticket.user.email_addr, email_msg)
        except Exception as exception:
            msg = "failed to send email:{}".format(exception)
            raise RuntimeError(msg)
        return

    def submit(self, filename):
        """Submit new OpenDACHS ticket.

        :param str filename: filename of ticket file
        """
        try:
            logger = logging.getLogger().getChild(self.submit.__name__)
            with open(filename) as fp:
                data = json.load(fp)
            ticket = self._initialize_ticket(data)
            self.archive(ticket)
            row = ticket.get_row()
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            sqlite_client.insert([row])
            self.dump_ticket(ticket)
            self.sendmail(ticket, "submitted")
        except Exception as exception:
            logger.exception("failed to submit OpenDACHS ticket %s", filename)
            msg = "failed to submit OpenDACHS ticket:{}".format(exception)
            raise RuntimeError(msg)
        finally:
            if "fp" in locals():
                fp.close()
        return

    def confirm(self, filename):
        """Confirm ticket.

        :param str filename: filename of ticket file
        """
        try:
            logger = logging.getLogger().getChild(self.confirm.__name__)
            with open(filename) as fp:
                data = json.load(fp)
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.update_row(
                "flag", "ticket", (data["flag"], data["ticket"])
            )
            ticket = src.ticket.Ticket.get_ticket(row)
            self.sendmail(ticket, "confirmed")
        except Exception as exception:
            logger.exception("failed to confirm OpenDACHS ticket %s", filename)
            msg = "failed to confirm ticket:{}".format(exception)
            raise RuntimeError(msg)
        return

    def accept(self, filename):
        """Accept ticket.

        :param str filename: filename of ticket file
        """
        try:
            logger = logging.getLogger().getChild(self.accept.__name__)
            with open(filename) as fp:
                data = json.load(fp)
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.select_row("ticket", (data["ticket"],))
            ticket = src.ticket.Ticket.get_ticket(row)
            archive = "storage/{}.warc".format(data["ticket"])
            os.rename(ticket.archive, archive)
            logger.info("moved WARC %s to storage", ticket.archive)
            sqlite_client.delete("ticket", [(data["ticket"],)])
            logger.info("deleted ticket %s", data["ticket"])
            ticket.flag = "deleted"
            self.dump_ticket(ticket)
            self.sendmail(ticket, "accepted")
        except Exception as exception:
            logger.exception("failed to accept OpenDACHS ticket %s", filename)
            msg = "failed to accept ticket:{}".format(exception)
            raise RuntimeError(msg)
        return

    def deny(self, filename):
        """Deny ticket.

        :param str filename: filename of ticket file
        """
        try:
            logger = logging.getLogger().getChild(self.deny.__name__)
            with open(filename) as fp:
                data = json.load(fp)
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.select_row("ticket", (data["ticket"],))
            ticket = src.ticket.Ticket.get_ticket(row)
            os.unlink(ticket.archive)
            sqlite_client.delete("ticket", [(data["ticket"],)])
            ticket.flag = "deleted"
            self.dump_ticket(ticket)
            self.sendmail(ticket, "denied")
        except Exception as exception:
            logger.exception("failed to deny OpenDACHS ticket %s", filename)
            msg = "failed to deny ticket:{}".format(exception)
            raise RuntimeError(msg)
        return

    def remove_expired(self):
        """Remove expired OpenDACHS tickets.

        :returns: number of removed tickets
        :rtype: int
        """
        try:
            logger = logging.getLogger().getChild(self.remove_expired.__name__)
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            parameters=(datetime.datetime.now() - datetime.timedelta(days=3),)
            rows = sqlite_client.select_rows(
                column="timestamp",
                parameters=parameters,
                operator="<"
            )
            tickets = [src.ticket.Ticket.get_ticket(row) for row in rows]
            counter = 0
            for ticket in tickets:
                if ticket.flag == "pending":
                    logger.info(
                        "remove expired ticket %s (timestamp %s)",
                        ticket.id_, ticket.timestamp
                    )
                    os.unlink(ticket.archive)
                    sqlite_client.delete("ticket", [(ticket.id_,)])
                    ticket.flag = "deleted"
                    self.dump_ticket(ticket)
                    self.sendmail(ticket, "expired")
                    counter += 1
        except Exception as exception:
            msg = "failed to remove expired OpenDACHS tickets:{}".format(
                exception
            )
            raise RuntimeError(msg)
        return counter

    def manage(self):
        """Manage OpenDACHS tickets."""
        try:
            logger = logging.getLogger().getChild(self.manage.__name__)
            managed = [0, 0, 0, 0, 0]
            logger.info("retrieve ticket files")
            files = src.ftp.retrieve_files(self.ftp)
            logger.info("retrieved %d tickets", len(files))
            for filename in files:
                try:
                    fp = open(filename)
                    data = json.load(fp)
                    if data["flag"] == "pending":
                        self.submit(filename)
                        managed[0] += 1
                    elif data["flag"] == "confirmed":
                        self.confirm(filename)
                        managed[1] += 1
                    elif data["flag"] == "accepted":
                        self.accept(filename)
                        managed[2] += 1
                    elif data["flag"] == "denied":
                        self.deny(filename)
                        managed[3] += 1
                    else:
                        msg = "failed to manage ticket:unknown flag {}".format(
                            data["flag"]
                        )
                        raise RuntimeError(msg)
                except Exception as exception:
                    logger.warning(
                        "failed to managed OpenDACHS ticket %s:%s",
                        filename,
                        exception
                    )
                finally:
                    if "fp" in locals():
                        fp.close()
            managed[4] += self.remove_expired()
            logger.info("submitted %d new tickets", managed[0])
            logger.info("confirmed %d tickets", managed[1])
            logger.info("accepted %d tickets", managed[2])
            logger.info("denied %d tickets", managed[3])
            logger.info("removed %d expired tickets", managed[4])
        except Exception as exception:
            msg = "failed to manage tickets:{}".format(exception)
            raise RuntimeError(msg)
        return
