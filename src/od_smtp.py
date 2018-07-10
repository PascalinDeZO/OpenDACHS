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
import json
import logging
import smtplib
import datetime

# third party imports
# library specific imports


def get_header_fields(smtp, file_):
    """Get header fields.

    :param ConfigParser smtp: SMTP configuration
    :param str file_: JSON file

    :returns: header fields
    :rtype: str
    """
    try:
        logger = logging.getLogger().getChild(get_header_fields.__name__)
        dest = json.load(open(file_))
        now = datetime.datetime.now()
        date = "Date: {}".format(now.strftime("%d %b %Y %H:%M"))
        from_ = "From: {}".format(smtp["msg"]["from"])
        reply_to = "Reply-To: {}".format(smtp["msg"]["reply_to"])
        to = "To: {}".format(dest["email"])
        subject = "Subject: {}".format(smtp["msg"]["subject"])
        header_fields = "\n".join([date, from_, reply_to, to, subject])
    except Exception:
        logger.exception("failed to get header fields")
        raise
    return header_fields


def get_body(smtp, file_, warc):
    """Get body.

    :param ConfigParser smtp: SMTP configuration
    :param str file_: JSON file
    :param str warc: WARC file

    :returns: body
    :rtype: str
    """
    try:
        logger = logging.getLogger().getChild(get_body.__name__)
        dest = json.load(open(file_))
        body = "\n".join(
            [
                smtp["msg"]["body"],
                "\n".join(
                    "{}:\t{}".format(k.capitalize(), v)
                    for k, v in dest.items()
                ),
            ]
        )
    except Exception:
        logger.exception("failed to get body")
        raise
    return body


def sendmails(smtp, warcs):
    """Send mail.

    :param ConfigParser smtp: SMTP configuration file
    :param list warcs: WARC files
    """
    try:
        logger = logging.getLogger().getChild(sendmails.__name__)
        smtp_client = smtplib.SMTP(
            host=smtp["SMTP"]["host"],
            port=smtp["SMTP"]["port"]
        )
        for file_, warc in warcs:
            dest = json.load(open(file_))
            header_fields = get_header_fields(smtp, file_)
            body = get_body(smtp, file_, warc)
            msg = "{}\n{}".format(header_fields, body)
            smtp_client.sendmail(smtp["msg"]["from"], dest["email"], msg)
    except Exception:
        logger.exception("failed to send mails")
        raise
    return
