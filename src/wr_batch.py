#    WR_Batch 1.0
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
:synopsis:
"""


# standard library imports
import os
import io
import csv
import logging
import argparse
import datetime

# third party imports
import requests
import warcio.warcwriter

# library specific imports


def get_argument_parser():
    """Get argument parser.

    :returns: argument parser
    :rtype: ArgumentParser
    """
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("csv", help="CSV file")
        parser.add_argument(
            "-o", "--output", default="warcs", help="output directory"
        )
    except Exception:
        raise
    return parser


def get_urls(args):
    """Get URLs.

    :param Namespace args: command-line arguments

    :returns: URLs
    :rtype: list
    """
    try:
        logger = logging.getLogger().getChild(get_urls.__name__)
        fp = open(args.csv)
        reader = csv.reader(fp)
        urls = [field for row in reader for field in row]
        logger.info("read %d URLs in", len(urls))
    except Exception:
        logger.exception("an exception was raised during reading of URLs")
        raise SystemExit
    finally:
        fp.close()
    return urls


def write_warc(url, file_):
    """Write WARC.

    :param str url: URL
    :param str file_: output file
    """
    try:
        logger = logging.getLogger().getChild(write_warc.__name__)
        fp = open(file_, "wb")
        writer = warcio.warcwriter.WARCWriter(fp, gzip=True)
        logger.info("send GET request {}".format(url))
        response = requests.get(url)
        if response.status_code != 200:
            raise RuntimeError(
                "{}:\tHTTP status code {}".format(url, response.status_code)
            )
        else:
            headers = response.content.headers.items()
            status_line = "200 OK"
            protocol="HTTP/1.0"
            status_and_headers = warcio.statusandheaders.StatusAndHeaders(
                status_line, headers, protocol=protocol
            )
            warc_record = writer.create_warc_record(
                url,
                "response",
                payload=io.BytesIO(response.content),
                http_headers=headers
            )
            writer.write_record(warc_record)
    except Exception:
        logger.exception("an exception was raised during writing of WARC")
        raise
    return


def write_warcs(args):
    """Write WARCS.

    :param Namespace args: command-line arguments
    """
    try:
        logger = logging.getLogger().getChild(write_warcs.__name__)
        urls = get_urls(args)
        if len(urls):
            now = datetime.datetime.now()
            now = now.strftime("%Y%m%d%H%M")
            dir_ = "{}/{}".format(args.output, now)
            os.makedirs(dir_, exist_ok=True)
            logger.info("created WARCs directory %s", dir_)
            for i, url in enumerate(urls):
                file_ = "{}/url_{}.warc.gz".format(dir_, i)
                try:
                    write_warc(url, file_)
                except RuntimeError:
                    logger.warning("%s has not been written to disk", url)
                    continue
                except Exception:
                    raise
        else:
            logger.warning("list of URLs is empty")
    except Exception:
        logger.exception("an exception was raised during writing of WARCs")
        raise SystemExit
    return


def main():
    """main routine."""
    try:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(main.__name__)
        parser = get_argument_parser()
        args = parser.parse_args()
        write_warcs(args)
    except Exception:
        logger.exception("an exception was raised")
        raise SystemExit
    return


if __name__ == "__main__":
    main()
