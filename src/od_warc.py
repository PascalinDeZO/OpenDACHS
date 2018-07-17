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
:synopsis: WARC input/output.
"""


# standard library imports
import io
import logging

# third party imports
import requests
import warcio

# library specific imports


def write_warc(url, warc):
    """Write WARC.

    :param str URL: URL
    :param str warc: WARC filename
    """
    try:
        logger = logging.getLogger().getChild(write_warc.__name__)
        fp = open(warc, mode="wb")
        writer = warcio.warcwriter.WARCWriter(fp, gzip=True)
        logger.info("send GET request {}".format(url))
        response = requests.get(url)
        if response.status_code != 200:
            raise RuntimeError(
                "{}:\tHTTP status code {}".format(url, response.status_code)
            )
        else:
            headers = response.raw.headers.items()
            status_line = "200 OK"
            protocol = "HTTP/1.x"
            status_and_headers = warcio.statusandheaders.StatusAndHeaders(
                status_line, headers, protocol=protocol
            )
            warc_record = writer.create_warc_record(
                url, "response",
                payload=io.BytesIO(response.content),
                http_headers=status_and_headers
            )
            writer.write_record(warc_record)
    except Exception:
        logger.exception("failed to write WARC %s", url)
        raise
    finally:
        fp.close()
    return warc
