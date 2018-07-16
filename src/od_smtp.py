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
:synopsis: SMTP client.
"""


# standard library imports
import logging
import smtplib
import datetime
import email.mime.text
import email.mime.multipart

# third party imports
# library specific imports


def set_header_fields(smtp, ticket, to_addrs, mimemultipart):
    """Set header fields.

    :param ConfigParser smtp: SMTP configuration
    :param str ticket: ticket
    :param str to_addrs: e-mail address recipient
    :param MIMEMultipart mimemultipart: MIME message

    :returns: mimemultipart
    :rtype: MIMEMultipart
    """
    try:
        logger = logging.getLogger().getChild(set_header_fields.__name__)
        now = datetime.datetime.now()
        mimemultipart["Date"] = now.strftime("%d %b %Y %H:%M")
        mimemultipart["From"] = smtp["header_fields"]["from"]
        mimemultipart["Reply-To"] = smtp["header_fields"]["reply_to"]
        mimemultipart["To"] = to_addrs
        subject = smtp["header_fields"]["subject"] + " {}".format(ticket)
        mimemultipart["Subject"] = subject
    except Exception:
        logger.exception("failed to get header fields")
        raise
    return mimemultipart


def get_body(smtp, flag):
    """Get body.

    :param ConfigParser smtp: SMTP configuration
    :param str flag: flag

    :returns: mimetext
    :rtype: MIMEText
    """
    try:
        logger = logging.getLogger().getChild(get_body.__name__)
        with open(smtp["body"][flag]) as fp:
            mimetext = email.mime.text.MIMEText(fp.read())
    except Exception:
        logger.exception("failed to get body")
        raise
    return mimetext


def get_attachment(ticket, attachment):
    """Get attachment.

    :param str ticket: ticket
    :param str attachment: attachment

    :returns: mimetext
    :rtype: MIMEText
    """
    try:
        logger = logging.getLogger().getChild(get_attachment.__name__)
        mimetext = email.mime.text.MIMEText(attachment)
        filename = "{}.txt".format(ticket)
        mimetext.add_header(
            "Content-Disposition", attachment, filename=filename
        )
    except Exception:
        logger.exception("failed to get attachment")
        raise
    return mimetext


def get_msg(smtp, ticket, to_addrs, flag, attachment=""):
    """Get e-mail.

    :param ConfigParser smtp: SMTP configuration
    :param str ticket: ticket
    :param str to_addrs: e-mail address recipient
    :param str flag: flag

    :returns: mimemultipart
    :rtype: MIMEMultipart
    """
    try:
        logger = logging.getLogger().getChild(get_msg.__name__)
        mimemultipart = email.mime.multipart.MIMEMultipart()
        mimemultipart = set_header_fields(
            smtp, ticket, to_addrs, mimemultipart
        )
        mimemultipart.attach(get_body(smtp, flag))
        if attachment:
            mimemultipart.attach(get_attachment(ticket, attachment))
    except Exception:
        logger.exception("failed to get e-mail")
        raise
    return mimemultipart


def sendmails(smtp, mails):
    """Send mail.

    :param ConfigParser smtp: SMTP configuration file
    :param list mails: mails
    """
    try:
        logger = logging.getLogger().getChild(sendmails.__name__)
        smtp_client = smtplib.SMTP(
            host=smtp["SMTP"]["host"],
            port=smtp["SMTP"]["port"]
        )
        for to_addrs, msg in mails:
            smtp_client.sendmail(
                smtp["header_fields"]["from"], to_addrs, msg.as_string()
            )
    except Exception:
        logger.exception("failed to send mails")
        raise
    return
