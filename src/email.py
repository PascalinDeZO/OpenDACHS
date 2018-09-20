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
:synopsis: Email composition and sending.
"""


# standard library imports
import logging
import smtplib
import datetime
import email.mime.text
import email.mime.multipart

# third party imports
# library specific imports


def read_in_template(name):
    """Read email template in.

    :param str name: name of email template to read in

    :returns: email template
    :rtype: str
    """
    try:
        fp = open("templates/{}.txt".format(name))
        template = fp.read()
    except OSError as exception:
        msg = "failed to open file templates/{}.txt:{}".format(name, exception)
        raise RuntimeError(msg)
    except Exception as exception:
        msg = "failed to read email template in:{}".format(exception)
        raise RuntimeError(msg)
    finally:
        if "fp" in locals():
            fp.close()
    return template


def compose_body(name, *args, **kwargs):
    """Compose email body.

    :param str name: name of email template
    :param args: replacement field values
    :param kwargs: replacement field values

    :returns: email body
    :rtype: MIMEText
    """
    try:
        template = read_in_template(name)
        body = template.format(*args, **kwargs)
        body = email.mime.text.MIMEText(body)
    except Exception as exception:
        msg = "failed to compose email body:{}".format(exception)
        raise RuntimeError(msg)
    return body


def compose_attachment(filename, text):
    """Compose email attachment.

    :param str filename: filename
    :param str text: text

    :returns: email attachment
    :rtype: MIMEText
    """
    try:
        attachment = email.mime.text.MIMEText(text)
        attachment.add_header(
            "Content-Disposition", "attachment", filename=filename
        )
    except Exception as exception:
        msg = "failed to compose email attachment:{}".format(exception)
        raise RuntimeError(msg)
    return attachment


def _add_header_fields(smtp, to_addrs, subject, msg):
    """Add header fields to email message.

    :param ConfigParser smtp: SMTP configuration
    :param str to_addrs: email recipient
    :param str subject: email subject
    :param MIMEMultipart msg: email message
    """
    try:
        now = datetime.datetime.now().strftime("%d %b %Y %H %M")
        msg["Date"] = now
        msg["From"] = smtp["header_fields"]["from"]
        msg["Reply-To"] = smtp["header_fields"]["reply_to"]
        msg["To"] = to_addrs
        msg["Subject"] = subject
    except Exception as exception:
        msg = "failed to add header fields:{}".format(exception)
        raise RuntimeError(msg)
    return


def compose_msg(smtp, to_addrs, subject, body, attachment=None):
    """Compose email message.

    :param ConfigParser smtp: SMTP configuration
    :param str to_addrs: email recipient
    :param str subject: email subject
    :param MIMEText body: email body
    :param attachment: email attachment if any
    :type: MIMEText or None

    :returns: email message
    :rtype: MIMEMultipart
    """
    try:
        msg = email.mime.multipart.MIMEMultipart()
        _add_header_fields(smtp, to_addrs, subject, msg)
        msg.attach(body)
        if attachment:
            msg.attach(attachment)
    except Exception as exception:
        msg = "failed to compose email message:{}".format(exception)
        raise RuntimeError(msg)
    return msg


def sendmail(smtp, to_addrs, msg):
    """Send email.

    :param ConfigParser smtp: SMTP configuration file
    :param str to_addrs: email recipient
    :param MIMEMultipart msg: email message
    """
    try:
        logger = logging.getLogger().getChild(sendmail.__name__)
        smtp_client = smtplib.SMTP(
            host=smtp["SMTP"]["host"], port=smtp["SMTP"]["port"]
        )
        smtp_client.sendmail(
            smtp["header_fields"]["from"], to_addrs, msg.as_string()
        )
        logger.info("sent email to %s", to_addrs)
    except Exception as exception:
        msg = "failed to send email:{}".format(exception)
        raise RuntimeError(msg)
    return
