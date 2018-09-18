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
import string
import logging
import datetime

# third party imports

# library specific imports
import src.od_ftp
import src.od_smtp
import src.od_warc
import src.od_sqlite
import src.od_api


class TicketManager(object):
    """Ticket manager.

    :cvar str TMP_WARCS_DIR: temporary WARCs output directory
    :cvar str PERMANENT_WARCS_DIR: permanent WARCs output directory
    :cvar str TEMPLATES_DIR: e-mail templates directory
    :cvar dict TEMPLATES: e-mail templates

    :ivar ConfigParser ftp: FTP configuration
    :ivar ConfigParser smtp: SMTP configuration
    :ivar SQLiteClient sqlite_client: OpenDACHS SQLite database client
    """
    TMP_WARCS_DIR = "tmp/warcs"
    PERMANENT_WARCS_DIR = "permanent/warcs"
    TEMPLATES_DIR = "templates"
    TEMPLATES = {
        "submitted": TEMPLATES_DIR + "/submitted.txt",
        "confirmed": TEMPLATES_DIR + "/confirmed.txt",
        "accepted": TEMPLATES_DIR + "/accepted.txt",
        "denied": TEMPLATES_DIR + "/denied.txt",
        "expired": TEMPLATES_DIR + "/expired.txt"
    }

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
            self.sqlite_client.create_table()
            os.makedirs(self.TMP_WARCS_DIR, exist_ok=True)
            os.makedirs(self.PERMANENT_WARCS_DIR, exist_ok=True)
        except Exception:
            logger.exception("failed to initialize ticket management")
            raise
        return

    #: https://stackoverflow.com/questions/3854692/generate-password-in-python
    @staticmethod
    def _generate_password(length=16):
        """Generate password.

        :param int length: length
        """
        alphabet = string.ascii_letters + string.digits
        password = "".join(
            alphabet[ord(char) % len(alphabet)]
            for char in base64.b64encode(os.urandom(length)).decode()
        )
        return password

    def _get_body(self, record):
        """Get body.

        :param dict record: record

        :returns: body
        :rtype: str
        """
        try:
            logger = logging.getLogger().getChild(self._get_body.__name__)
            with open(self.TEMPLATES[record["flag"]]) as fp:
                template = fp.read()
            if record["flag"] == "submitted" or record["flag"] == "confirmed":
                body = template.format(
                    ticket=record["ticket"],
                    username=record["username"],
                    password=record["password"]
                )
            elif record["flag"] == "accepted" or record["flag"] == "denied":
                body = template.format(
                    ticket=record["ticket"],
                    reply_to=self.smtp["header_fields"]["reply_to"]
                )
        except Exception:
            logger.exception("failed to get body")
            raise
        return body

    @staticmethod
    def _get_opendachs_information(raw):
        """Get OpenDACHS information.

        :param dict raw: raw data

        :returns: OpenDACHS information
        :rtype: str
        """
        opendachs_information = ""
        for key, value in sorted(list(raw.items()), key=lambda x: x[0]):
            if key not in ["email", "url", "ticket"]:
                continue
            else:
                if key == "email":
                    info = "E-Mail\t: {}\n"
                elif key == "url":
                    info = "URL\t: {}\n"
                else:
                    info = "{}\t: {{}}\n".format(key.title())
                opendachs_information += info.format(value)
        return opendachs_information

    @staticmethod
    def _get_resource_information(raw):
        """Get resource information.

        :param dict raw: raw data

        :returns: resource information
        :rtype: str
        """
        resource_information = ""
        for key, value in sorted(list(raw.items()), key=lambda x: x[0]):
            if key in ["email", "url", "ticket", "flag"]:
                continue
            elif key == "creator":
                for creator in value:
                    resource_information += "Creator(s):\n"
                    resource_information += (
                        "\n".join(
                            "\t{}\t: {}".format(k.title(), v)
                            for k, v in creator.items()
                        ) + "\n"
                    )
            elif key in ["title", "publisher"]:
                resource_information += "{}(s):\n".format(key.title())
                resource_information += (
                    "\n".join(
                        "\t{}\t:{}".format(k.title(), v)
                        for k, v in value.items()
                    ) + "\n"
                )
            elif key in ["subjectHeading", "personHeading"]:
                if key == "subjectHeading":
                    resource_information += "Subject Heading(s):\n"
                else:
                    resource_information += "Person Heading(s):\n"
                if any(value):
                    resource_information += (
                        "\n".join(heading for heading in value if heading) +
                        "\n"
                    )
            elif key in [
                "publicationDate", "generalResourceType", "resourceType"
            ]:
                if key == "publicationDate":
                    resource_information += (
                        "Publication Date\t: {}\n".format(value)
                    )
                    date = re.compile("([0-9]{4})[0-9]{4}")
                    match = date.match(value)
                    resource_information += (
                        "Publication Year\t: {}\n".format(match.group(1))
                    )
                elif key == "generalResourceType":
                    resource_information += (
                        "General Resource Type\t: {}\n".format(value)
                    )
                else:
                    resource_information += (
                        "Resource Type\t: {}\n".format(value)
                    )
        return resource_information

    def _get_plaintext(self, raw):
        """Get plaintext attachment.

        :param dict raw: raw data

        :returns: plaintext attachment
        :rtype: str
        """
        try:
            logger = logging.getLogger().getChild(self._get_plaintext.__name__)
            attachment = "OPENDACHS REQUEST INFORMATION:\n{}\n".format(
                self._get_opendachs_information(raw)
            )
            attachment += "RESOURCE INFORMATION:\n{}\n".format(
                self._get_resource_information(raw)
            )
        except Exception:
            logger.exception("failed to get plaintext attachment")
            raise
        return attachment

    def _get_ris(self, raw):
        """Get RIS attachment.

        :param dict raw: raw

        :returns: RIS attachment
        :rtype: str
        """
        try:
            logger = logging.getLogger().getChild(self._get_ris.__name__)
            tags = {
                "resourceType": "TY",
                "creator": "A{}",
                "publicationDate": "DA",
                "keyword": "KW",
                "url": "UR",
                "publisher": "PB",
                "title": "TI{}",
            }
            tag = "{tag}\u0020\u0020-\u0020{value}\u000A"
            keyword = ""
            attachment = tag.format(tag="TY", value=raw["resourceType"])
            for key, value in raw.items():
                if key in ["email", "ticket", "flag"]:
                    continue
                elif key == "creator":
                    for i in range(len(value)):
                        attachment += tag.format(
                            tag=tags[key].format(i+1),
                            value=value[i]["romanization"]
                        )
                elif key == "title":
                    attachment += tag.format(
                        tag=tags[key].format(1), value=value["romanization"]
                    )
                    if value["script"]:
                        attachment += tag.format(
                            tag=tags[key].format(2), value=value["script"]
                        )
                elif key == "publisher":
                    attachment += tag.format(
                        tag=tags[key], value=value["romanization"]
                    )
                elif key == "publicationDate":
                    date = re.compile("([0-9]{4})([0-9]{2})([0-9]{2})")
                    match = date.match(value)
                    attachment += tag.format(
                        tag=tags[key],
                        value="{}/{}/{}".format(
                            match.group(1), match.group(2), match.group(3)
                        )
                    )
                elif key in ["subjectHeading", "personHeading"]:
                    keyword += ", ".join(v for v in value)
            if keyword:
                attachment += tag.format(tag=tags["keyword"], value=keyword)
            attachment += tag.format(tag="ER", value="")
        except Exception:
            logger.exception("failed to get RIS attachment")
            raise
        return attachment

    def _get_attachment(self, record):
        """Get attachment.

        :param dict record: record

        :returns: attachment
        :rtype: str
        """
        try:
            logger = logging.getLogger().getChild(
                self._get_attachment.__name__
            )
            if record["flag"] == "submitted" or record["flag"] == "confirmed":
                attachment = self._get_plaintext(json.loads(record["raw"]))
            elif record["flag"] == "accepted":
                attachment = self._get_ris(json.loads(record["raw"]))
        except Exception:
            logger.exception("failed to get attachment")
            raise
        return attachment

    def submit_ticket(self, file_):
        """Submit ticket.

        :param str file_: local file
        """
        try:
            logger = logging.getLogger().getChild(self.submit_ticket.__name__)
            dest = json.load(open(file_))
            if dest["flag"] == "pending":
                dest["flag"] = "submitted"
            else:
                raise RuntimeError("unexpected  flag '%s'", dest["flag"])
            dest["username"] = "OpenDACHS ticket {}".format(dest["ticket"])
            dest["password"] = self._generate_password()
            timestamp = datetime.datetime.now()
            warc = "{}/{}.warc".format(self.TMP_WARCS_DIR, dest["ticket"])
            src.od_warc.write_warc(dest["url"], warc)
            parameters = []
            for k in self.sqlite_client.sqlite["column_defs"].keys():
                if k not in ["timestamp", "warc"]:
                    if k == "raw":
                        parameters.append(json.dumps(dest))
                    else:
                        parameters.append(dest[k])
                elif k == "timestamp":
                    parameters.append(timestamp)
                elif k == "warc":
                    parameters.append(warc)
            #: create user (Webrecorder)
            role = "archivist"
            desc = "OpenDACHS ticket"
            filename = "/{}".format(warc)
            args = [
                "create",
                dest["username"],
                dest["password"],
                role,
                desc,
                filename
            ]
            src.od_api.api_call(args)
            parameters = tuple(parameters)
            subject = "Your OpenDACHS request " + dest["ticket"]
            body = self._get_body(dest)
            tmp = {
                k: v for k, v in dest.items()
                if k in ["ticket", "email", "flag", "timestamp", "warc"]
            }
            tmp["raw"] = json.dumps(dest)
            attachment = self._get_attachment(tmp)
            msg = src.od_smtp.get_msg(
                self.smtp, dest["email"], subject, body, attachment=attachment
            )
            self.sqlite_client.insert([parameters])
            src.od_smtp.sendmail(self.smtp, dest["email"], msg)
        except Exception as exception:
            logger.exception("failed to submit ticket\t: %s", exception)
            raise
        return

    def confirm_ticket(self, file_):
        """Confirm ticket.

        :param str file_: local file
        """
        try:
            logger = logging.getLogger().getChild(self.confirm_ticket.__name__)
            dest = json.load(open(file_))
            parameters = (dest["ticket"],)
            record = self.sqlite_client.select(parameters)[0]
            if record:
                if record["flag"] != "submitted":
                    logger.warning("unexpected flag '%s'", record["flag"])
                else:
                    parameters = (dest["flag"], dest["ticket"])
                    self.sqlite_client.update([parameters])
                    body = self._get_body(dest)
                    subject = "OpenDACHS request " + dest["ticket"]
                    attachment = self._get_attachment(record)
                    msg = src.od_smtp.get_msg(
                        self.smtp,
                        self.smtp["header_fields"]["reply_to"],
                        subject,
                        body,
                        attachment=attachment
                    )
                    src.od_smtp.sendmail(
                        self.smtp,
                        self.smtp["header_fields"]["reply_to"],
                        msg
                    )
            else:
                raise RuntimeError("unknown ticket %s", dest["ticket"])
        except Exception as exception:
            logger.exception("failed to confirm ticket\t: %s", exception)
            raise
        return

    def accept_ticket(self, file_):
        """Accept ticket.

        :param str file_: local file
        """
        try:
            logger = logging.getLogger().getChild(self.accept_ticket.__name__)
            dest = json.load(open(file_))
            parameters = (dest["ticket"],)
            record = self.sqlite_client.select(parameters)[0]
            if record:
                if record["flag"] != "confirmed":
                    logger.warning("unexpected flag '%s'", record["flag"])
                else:
                    warc = record["warc"].rsplit("/")[-1]
                    dst = "{}/{}".format(self.PERMANENT_WARCS_DIR, warc)
                    os.rename(record["warc"], dst)
                    logger.info(
                        "moved WARC %s to permanent WARC output directory",
                        warc
                    )
                    self.sqlite_client.delete([parameters])
                    logger.info("deleted ticket %s", dest["ticket"])
                    body = self._get_body(dest)
                    subject = "Your OpenDACHS request " + dest["ticket"]
                    tmp = {k: v for k, v in record.items() if k != "flag"}
                    tmp["flag"] = "accepted"
                    attachment = self._get_attachment(tmp)
                    msg = src.od_smtp.get_msg(
                        self.smtp, record["email"], subject, body,
                        attachment=attachment, format_="ris"
                    )
                    src.od_smtp.sendmail(
                        self.smtp, record["email"], msg
                    )
            else:
                raise RuntimeError("unknown ticket %s", dest["ticket"])
        except Exception as exception:
            logger.exception("failed to accept ticket\t: %s", exception)
            raise
        return

    def deny_ticket(self, file_):
        """Deny ticket.

        :param str file_: local file
        """
        try:
            logger = logging.getLogger().getChild(self.deny_ticket.__name__)
            dest = json.load(open(file_))
            parameters = (dest["ticket"],)
            record = self.sqlite_client.select(parameters)[0]
            if record:
                if record["flag"] != "confirmed":
                    logger.warning("unexpected flag '%s'", record["flag"])
                else:
                    os.unlink(record["warc"])
                    warc = record["warc"].rsplit("/")[-1]
                    logger.info(
                        "removed WARC %s from temporary WARC output directory",
                        warc
                    )
                    self.sqlite_client.delete([parameters])
                    logger.info("deleted ticket %s", dest["ticket"])
                    body = self._get_body(dest)
                    subject = "Your OpenDACHS request " + dest["ticket"]
                    msg = src.od_smtp.get_msg(
                        self.smtp, record["email"], subject, body
                    )
                    src.od_smtp.sendmail(
                        self.smtp, record["email"], msg
                    )
            else:
                raise RuntimeError("unknown ticket %s", dest["ticket"])
        except Exception as exception:
            logger.exception("failed to deny ticket\t: %s", exception)
            raise
        return

    def manage_ticket(self, file_):
        """Manage ticket.

        :param str file_: local file

        :returns: managed_ticket
        :rtype: list
        """
        try:
            logger = logging.getLogger().getChild(self.manage_ticket.__name__)
            managed_ticket = [0, 0, 0, 0]
            dest = json.load(open(file_))
            if dest["flag"] == "pending":
                self.submit_ticket(file_)
                managed_ticket[0] += 1
            elif dest["flag"] == "confirmed":
                self.confirm_ticket(file_)
                managed_ticket[1] += 1
            elif dest["flag"] == "accepted":
                self.accept_ticket(file_)
                managed_ticket[2] += 1
            elif dest["flag"] == "denied":
                self.deny_ticket(file_)
                managed_ticket[3] += 1
        except Exception:
            logger.exception("failed to manage ticket %s", dest["ticket"])
            raise
        finally:
            os.unlink(file_)
        return managed_ticket

    def remove_expired(self):
        """Remove expired tickets.

        :returns: number of expired tickets
        :rtype: int
        """
        return 0

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
            managed_tickets = [0, 0, 0, 0]
            for file_ in files:
                try:
                    managed_tickets = [
                        x + y
                        for x, y in
                        zip(managed_tickets, self.manage_ticket(file_))
                    ]
                except Exception as exception:
                    logger.warning("failed to manage ticket\t: %s", exception)
            managed_tickets.append(self.remove_expired())
            logger.info("submitted %d new tickets", managed_tickets[0])
            logger.info("confirmed %d tickets", managed_tickets[1])
            logger.info("accepted %d tickets", managed_tickets[2])
            logger.info("denied %d tickets", managed_tickets[3])
            logger.info("removed %d expired tickets", managed_tickets[4])
        except Exception:
            logger.exception("failed to prcocess files")
            raise
        return
