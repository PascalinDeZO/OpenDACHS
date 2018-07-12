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
:synopsis: FTP client
"""


# standard library imports
import ftplib
import logging
import tempfile

# third party imports
# library specific imports


def _get_ftp_client(ftp):
    """Get FTP client.

    :param ConfigParser ftp: FTP configuration

    :returns: FTP client
    :rtype: FTP_TLS
    """
    try:
        logger = logging.getLogger().getChild(_get_ftp_client.__name__)
        ftp_client = ftplib.FTP_TLS(**ftp["FTP"])
        ftp_client.prot_p()
    except Exception:
        logger.exception("failed to get FTP client")
        raise
    return ftp_client


def retrieve_file(ftp_client, file_):
    """Retrieve file.

    :param FTP_TLS ftp_client: FTP client
    :param str file_: filename

    :returns: local file
    :rtype: str
    """
    try:
        logger = logging.getLogger().getChild(retrieve_file.__name__)
        fp = tempfile.NamedTemporaryFile(delete=False)
        ftp_client.retrbinary("RETR {}".format(file_), fp.write)
        fp.close()
        ftp_client.delete(file_)
    except Exception:
        logger.exception("failed to retrieve file %s", file_)
        raise
    return fp.name


def retrieve_files(ftp):
    """Retrieve files.

    :param ConfigParser ftp: FTP configuration

    :returns: local files
    :rtype: list
    """
    try:
        logger = logging.getLogger().getChild(retrieve_files.__name__)
        ftp_client = _get_ftp_client(ftp)
        local_files = []
        for file_ in ftp_client.nlst(ftp["cmd"]["RETR"]):
            try:
                local_files.append(retrieve_file(ftp_client, file_))
            except Exception:
                logger.warning("failed to retrieve file %s", file_)
    except Exception:
        logger.exception("failed to retrieve files")
        raise
    return local_files
