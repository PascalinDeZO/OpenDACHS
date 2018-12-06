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
:synopsis: FTP client.
"""


# standard library imports
import ftplib
import logging
import tempfile

# third party imports
# library specific imports


def get_ftp_client(ftp):
    """Get FTP client.

    :param ConfigParser ftp: FTP configuration

    :returns: FTP client
    :rtype: FTP_TLS
    """
    try:
        ftp_client = ftplib.FTP_TLS(**ftp["FTP"])
        ftp_client.prot_p()
    except Exception as exception:
        raise RuntimeError(
            "failed to get FTP client"
        ) from exception
    return ftp_client


def retrieve_file(ftp_client, filename):
    """Retrieve file.

    :param FTP_TLS ftp_client: FTP client
    :param str filename: filename

    :returns: local file filename
    :rtype: str
    """
    try:
        fp = tempfile.NamedTemporaryFile(delete=False)
        ftp_client.retrbinary("RETR {}".format(filename), fp.write)
        fp.close()
        ftp_client.delete(filename)
    except Exception as exception:
        raise RuntimeError(
            "failed to retrieve file {filename}".format(filename=filename)
        ) from exception
    return fp.name


def retrieve_files(ftp):
    """Retrieve files.

    :param ConfigParser ftp: FTP configuration

    :returns: list of local file filenames
    :rtype: str
    """
    try:
        logger = logging.getLogger().getChild(retrieve_files.__name__)
        ftp_client = get_ftp_client(ftp)
        filenames = []
        for filename in ftp_client.nlst(ftp["cmd"]["RETR"]):
            try:
                filenames.append(retrieve_file(ftp_client, filename))
            except Exception as exception:
                logger.warning("failed to retrieve file %s", filename)
    except Exception as exception:
        raise RuntimeError(
            "failed to retrieve files"
        ) from exception
    return filenames