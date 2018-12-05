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
import urllib.parse
import subprocess
import sqlite3

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
        :param ConfigParser sqlite: SQLite configuration
        """
        try:
            self.ftp = ftp
            self.smtp = smtp
            self.sqlite = sqlite
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            sqlite_client.create_table()
        except sqlite3.Error as exception:
            raise RuntimeError(
                "failed to initialize ticket manager"
            ) from exception
        return

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
            raise RuntimeError(
                "failed to generate username"
            ) from exception
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
            if length < 1:
                raise ValueError("length < 1")
            alphabet = string.ascii_letters + string.digits
            password = "".join(
                alphabet[ord(char) % len(alphabet)]
                for char in base64.b64encode(os.urandom(length)).decode()
            )
        except Exception as exception:
            raise RuntimeError(
                "failed to generate password"
            ) from exception
        return password

    @staticmethod
    def _get_url(url, base_src_url):
        """Get absolute src URL.

        :param str url: request URL
        :param str base_src_url: base src URL

        :returns: absolute src URL
        :rtype: str
        """
        try:
            if base_src_url.startswith(("https", "http")):
                abs_src_url = base_src_url
            elif base_src_url.startswith("//"):
                parse_result = urllib.parse.urlparse(url)
                abs_src_url = "{}:{}".format(
                    parse_result.scheme, base_src_url
                )
            elif base_src_url.startswith("/"):
                parse_result = urllib.parse.urlparse(url)
                abs_src_url = "{}://{}{}".format(
                    parse_result.scheme,
                    parse_result.hostname,
                    base_src_url
                )
            else:
                abs_src_url = "{}/{}".format(url, base_src_url)
        except Exception as exception:
            raise RuntimeError(
                "failed to get absolute src URL"
            ) from exception
        return abs_src_url

    def _get_image_urls(self, response):
        """Archive images.

        :param Response response: response
        """
        try:
            soup = bs4.BeautifulSoup(response.content, features="html.parser")
            for img in soup.find_all("img"):
                yield(self._get_url(response.request.url, img["src"]))
        except Exception as exception:
            raise RuntimeError(
                "failed to get image URLs"
            ) from exception

    def _get_media_urls(self, response):
        """Get media URLs.

        :param Response response: response
        """
        try:
            soup = bs4.BeautifulSoup(response.content, features="html.parser")
            for source in soup.find_all("source"):
                if "src" in source.attrs:
                    yield(self._get_url(response.request.url, source["src"]))
                elif "srcset" in source.attrs:
                    yield(self._get_url(response.request.url, source["srcset"]))
        except Exception as exception:
            raise RuntimeError(
                "failed to get media URLs"
            ) from exception

    def _get_css_urls(self, response):
        """Get CSS URLs.

        :param Response response: response
        """
        try:
            soup = bs4.BeautifulSoup(
                response.content, features="html.parser"
            )
            head = soup.find("head")
            if head:
                for link in head.find_all("link"):
                    """
                    FIXME for some reason, bs4 does not respect the self-closing
                    tag 'link', which leads to its 'rel' attribute becoming a
                    list
                    """
                    if link["rel"][0] == "stylesheet":
                        yield(
                            self._get_url(response.request.url, link["href"])
                        )
        except Exception as exception:
            raise RuntimeError(
                "failed to get CSS URLs"
            ) from exception

    def archive(self, ticket):
        """Archive URL.

        Code snippet see https://github.com/webrecorder/warcio

        :param Ticket ticket: OpenDACHS ticket
        """
        try:
            scraper = cfscrape.create_scraper()
            with warcio.capture_http.capture_http(ticket.archive):
                response = scraper.get(ticket.metadata["url"])
                image_urls = self._get_image_urls(response)
                for image_url in image_urls:
                    scraper.get(image_url)
                media_urls = self._get_media_urls(response)
                for media_url in media_urls:
                    scraper.get(media_url)
                css_urls = self._get_css_urls(response)
                for css_url in css_urls:
                    scraper.get(css_url)
        except Exception as exception:
            raise RuntimeError(
                "failed to archive {url}".format(url=ticket.metadata["url"])
            ) from exception
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
            raise RuntimeError(
                "failed to dump OpenDACHS ticket {id}".format(id=ticket.id_)
            ) from exception
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
            raise RuntimeError(
                "failed to return prettyprint"
            ) from exception
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
            raise RuntimeError(
                "failed to compose plaintext email attachment"
            ) from exception
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
        except Exception as exception:
            raise RuntimeError(
                "failed to compose RIS attachment"
            ) from exception
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
            raise RuntimeError(
                "failed to initialize Webrecorder user"
            ) from exception
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
            raise RuntimeError(
                "failed to initialize OpenDACHS ticket"
            ) from exception
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
                raise ValueError(
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
        except Exception as exception:
            raise RuntimeError("failed to send email") from exception
        return

    def submit(self, data):
        """Submit new OpenDACHS ticket.

        :param dict data: OpenDACHS ticket
        """
        logger = logging.getLogger().getChild(self.submit.__name__)
        try:
            ticket = self._initialize_ticket(data)
            self.archive(ticket)
            row = ticket.get_row()
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            sqlite_client.insert([row])
            self.dump_ticket(ticket)
        except Exception as exception:
            logger.exception(
                "failed to submit OpenDACHS ticket %s", data["ticket"]
            )
            raise RuntimeError(
                "failed to submit OpenDACHS ticket"
            ) from exception
        return

    def confirm(self, data):
        """Confirm ticket.

        :param dict data: OpenDACHS ticket

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        logger = logging.getLogger().getChild(self.confirm.__name__)
        try:
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.update_row(
                "flag", "ticket", (data["flag"], data["ticket"])
            )
            ticket = src.ticket.Ticket.get_ticket(row)
        except Exception as exception:
            logger.exception(
                "failed to confirm OpenDACHS ticket %s", data["ticket"]
            )
            raise RuntimeError(
                "failed to confirm OpenDACHS ticket {id}".format(
                    id=data["ticket"]
                )
            ) from exception
        return ticket

    def accept(self, data):
        """Accept ticket.

        :param dict data: OpenDACHS ticket

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        logger = logging.getLogger().getChild(self.accept.__name__)
        try:
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.select_row("ticket", (data["ticket"],))
            ticket = src.ticket.Ticket.get_ticket(row)
            storage = "storage/{ticket}".format(ticket=data["ticket"])
            path = "./../webrecorder/data/warcs{user}".format(
                user=ticket.user.username
            )
            if not os.access(path, os.F_OK):
                path = "tmp/warcs/{ticket}.warc".format(ticket=ticket.id_)
            shutil.copytree(path, storage)
            os.unlink(ticket.archive)
            logger.info("moved WARC %s to storage", ticket.archive)
            sqlite_client.delete("ticket", [(ticket.id_,)])
            logger.info("deleted ticket %s", ticket.id_)
            ticket.flag = "deleted"
            self.dump_ticket(ticket)
        except Exception as exception:
            logger.exception(
                "failed to accept OpenDACHS ticket %s", data["ticket"]
            )
            raise RuntimeError(
                "failed to accept OpenDACHS ticket {id}".format(
                    id=data["ticket"]
                )
            ) from exception
        return ticket

    def deny(self, data):
        """Deny ticket.

        :param dict data: OpenDACHS ticket

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        logger = logging.getLogger().getChild(self.deny.__name__)
        try:
            sqlite_client = src.sqlite.SQLiteClient(self.sqlite)
            row = sqlite_client.select_row("ticket", (data["ticket"],))
            ticket = src.ticket.Ticket.get_ticket(row)
            os.unlink(ticket.archive)
            sqlite_client.delete("ticket", [(ticket.id_,)])
            ticket.flag = "deleted"
            self.dump_ticket(ticket)
        except Exception as exception:
            logger.exception(
                "failed to deny OpenDACHS ticket %s", data["ticket"])
            raise RuntimeError(
                "failed to deny OpenDACHS ticket {id}".format(id=data["ticket"])
            ) from exception
        return ticket

    def remove_expired(self):
        """Remove expired OpenDACHS tickets."""
        logger = logging.getLogger().getChild(self.remove_expired.__name__)
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
                if ticket.flag == "pending":
                    logger.info(
                        "remove expired ticket %s (timestamp %s)",
                        ticket.id_, ticket.timestamp
                    )
                    os.unlink(ticket.archive)
                    sqlite_client.delete("ticket", [(ticket.id_,)])
                    ticket.flag = "deleted"
                    self.dump_ticket(ticket)
                    yield(ticket)
        except Exception as exception:
            raise RuntimeError(
                "failed to remove expired OpenDACHS tickets"
            ) from exception

    def call_api(self):
        """Call Webrecorder API."""
        # FIXME stdout is not logged
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
            raise RuntimeError(
                "failed to call Webrecorder API (exit status {})".format(
                    child.returncode
                )
            )

    def manage(self):
        """Manage OpenDACHS tickets."""
        logger = logging.getLogger().getChild(self.manage.__name__)
        logger.info("retrieve ticket files")
        files = src.ftp.retrieve_files(self.ftp)
        logger.info("retrieved %d tickets", len(files))
        submitted = confirmed = accepted = denied = removed = 0
        for filename in files:
            try:
                fp = open(filename)
                data = json.load(fp)
                if data["flag"] == "pending":
                    ticket = self.submit(data)
                    self.call_api()
                    submitted += 1
                    self.sendmail(ticket, "submitted")
                elif data["flag"] == "confirmed":
                    ticket = self.confirm(data)
                    confirmed += 1
                    self.sendmail(ticket, "confirmed")
                elif data["flag"] == "accepted":
                    ticket = self.accept(data)
                    self.call_api()
                    accepted += 1
                    self.sendmail(ticket, "accepted")
                elif data["flag"] == "denied":
                    ticket = self.deny(data)
                    self.call_api()
                    denied += 1
                    self.sendmail(ticket, "denied")
                else:
                    msg = "unknown flag {flag}".format(flag=data["flag"])
                    raise Exception(msg)
            except Exception as exception:
                logger.warning("failed to manage ticket")
                if "ticket" not in locals() and "data" not in locals():
                    ticket = src.ticket.Ticket("unknown", *(5*(None, )))
                elif "data" in locals():
                    ticket = src.ticket.Ticket(data["ticket"], *(5*(None, )))
                self.sendmail(ticket, "error")
                raise RuntimeError(
                    "failed to manage ticket"
                ) from exception
            finally:
                if "fp" in locals():
                    fp.close()
        for ticket in self.remove_expired():
            try:
                self.call_api()
                removed += 1
                self.sendmail(ticket, "expired")
            except Exception as exception:
                logger.warning(
                    "failed to remove expired ticket {id}".format(id=ticket.id_)
                )
                self.sendmail(ticket, "error")
                raise RuntimeError(
                    "failed to remove expired ticket {id}".format(id=ticket.id_)
                )
        logger.info("submitted %d new tickets", submitted)
        logger.info("confirmed %d tickets", confirmed)
        logger.info("accepted %d tickets", accepted)
        logger.info("denied %d tickets", denied)
        logger.info("removed %d expired tickets", removed)
        return