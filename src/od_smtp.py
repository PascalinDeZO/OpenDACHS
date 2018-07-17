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


def set_header_fields(smtp, to_addrs, subject, mimemultipart):
    """Set header fields.

    :param ConfigParser smtp: SMTP configuration
    :param str to_addrs: e-mail address recipient
    :param str subject: subject
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
        mimemultipart["Subject"] = subject
    except Exception:
        logger.exception("failed to get header fields")
        raise
    return mimemultipart


def get_body(body):
    """Get body.

    :param str body: body

    :returns: mimetext
    :rtype: MIMEText
    """
    try:
        logger = logging.getLogger().getChild(get_body.__name__)
        mimetext = email.mime.text.MIMEText(body)
    except Exception:
        logger.exception("failed to get body")
        raise
    return mimetext


def get_attachment(attachment):
    """Get attachment.

    :param str attachment: attachment

    :returns: mimetext
    :rtype: MIMEText
    """
    try:
        logger = logging.getLogger().getChild(get_attachment.__name__)
        mimetext = email.mime.text.MIMEText(attachment)
        mimetext.add_header(
            "Content-Disposition", attachment, filename="info.txt"
        )
    except Exception:
        logger.exception("failed to get attachment")
        raise
    return mimetext


def get_msg(smtp, to_addrs, subject, body, attachment=""):
    """Get e-mail.

    :param ConfigParser smtp: SMTP configuration
    :param str to_addrs: e-mail address recipient
    :param str subject: subject
    :param str body: body
    :param str attachment: attachment

    :returns: mimemultipart
    :rtype: MIMEMultipart
    """
    try:
        logger = logging.getLogger().getChild(get_msg.__name__)
        mimemultipart = email.mime.multipart.MIMEMultipart()
        mimemultipart = set_header_fields(
            smtp, to_addrs, subject, mimemultipart
        )
        mimemultipart.attach(get_body(body))
        if attachment:
            mimemultipart.attach(get_attachment(attachment))
    except Exception:
        logger.exception("failed to get e-mail")
        raise
    return mimemultipart


def sendmail(smtp, to_addrs, msg):
    """Send mail.

    :param ConfigParser smtp: SMTP configuration file
    :param MIMEMultipart msg: e-mail
    """
    try:
        logger = logging.getLogger().getChild(sendmail.__name__)
        smtp_client = smtplib.SMTP(
            host=smtp["SMTP"]["host"],
            port=smtp["SMTP"]["port"]
        )
        smtp_client.sendmail(
            smtp["header_fields"]["from"], to_addrs, msg.as_string()
        )
    except Exception:
        logger.exception("failed to send mail")
        raise
    return
