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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>


"""
:synopsis: Web scraping.
"""

# standard library imports
import urllib

# third party imports
import bs4
import warcio.capture_http
import cfscrape

# library specific imports


class Scraper(object):
    """Web scraper.

    :ivar Ticket ticket: OpenDACHS ticket
    :ivar Response response: response to HTTP request
    :ivar BeautifulSoup soup: tree
    """

    def __init__(self, ticket):
        """Initialize Web scraper.

        :param Ticket ticket: OpenDACHS ticket
        """
        try:
            self.ticket = ticket
            self.response = self._request()
            self.soup = bs4.BeautifulSoup(
                self.response.content, features="html.parser"
            )
            self.base = self._get_base()
        except Exception as exception:
            raise RuntimeError(
                "failed to initialize Web scraper"
            ) from exception

    def _request(self):
        """Send HTTP request.

        :returns: response to HTTP request
        :rtype: Response
        """
        try:
            scraper = cfscrape.create_scraper()
            with warcio.capture_http.capture_http(self.ticket.archive):
                response = scraper.get(self.ticket.metadata["url"])
        except Exception as exception:
            raise RuntimeError(
                "failed to send HTTP request"
            ) from exception
        return response

    def _get_base(self):
        """Get base URL.

        :returns: base URL
        :rtype: str
        """
        try:
            base = self.soup.find("base")
            if base:
                base = base["href"]
            else:
                base = self.ticket.metadata["url"]
        except Exception as exception:
            raise RuntimeError("failed to get base URL") from exception
        return base

    def get_absolute_url(self, relative):
        """Get absolute URL.

        :param str relative: relative URL

        :returns: absolute URL
        :rtype: str
        """
        try:
            if relative.startswith(("https", "http")):
                absolute = relative
            elif relative.startswith("//"):
                parse_result = urllib.parse.urlparse(self.base)
                absolute = "{scheme}:{relative}".format(
                    scheme=parse_result.scheme, relative=relative
                )
            elif relative.startswith("/"):
                parse_result = urllib.parse.urlparse(self.base)
                absolute = "{scheme}://{hostname}{relative}".format(
                    scheme=parse_result.scheme,
                    hostname=parse_result.hostname,
                    relative=relative
                )
            else:
                absolute = "{base}/{relative}".format(
                    base=self.base, relative=relative
                )
        except Exception as exception:
            raise RuntimeError("failed to get absolute URL") from exception
        return absolute

    def get_link_tag_urls(self):
        """Get <link> tag URLs (stylesheet only).

        :returns: <link> tag URL
        :rtype: str
        """
        try:
            for link in self.soup.find_all("link"):
                if link["rel"][0] == "stylesheet":
                    yield(self.get_absolute_url(link["href"]))
        except Exception as exception:
            raise RuntimeError("failed to get <link> URLs") from exception

    def get_script_tag_urls(self):
        """Get <script> tag URLs.

        :returns: <script> tag URL
        :rtype: str
        """
        try:
            for script in self.soup.find_all("script"):
                if "src" in script.attrs:
                    yield(self.get_absolute_url(script["src"]))
        except Exception as exception:
            raise RuntimeError("failed to get <script> URLs") from exception

    def get_img_tag_urls(self):
        """Get <img> tag URLs.

        :returns: <img> tag URL
        :rtype: str
        """
        try:
            for img in self.soup.find_all("img"):
                yield(self.get_absolute_url(img["src"]))
        except Exception as exception:
            raise RuntimeError("failed to get <img> URLs") from exception

    def get_video_tag_urls(self):
        """Get <video> tag URLs.

        :returns: <video> tag URL
        :rtype: str
        """
        try:
            for video in self.soup.find_all("video"):
                for source in video.find_all("source"):
                    yield(self.get_absolute_url(source["src"]))
        except Exception as exception:
            raise RuntimeError("failed to get <video> URLs")

    def get_audio_tag_urls(self):
        """Get <audio> tag URLs.

        :returns: <audio> tag URL
        :rtype: str
        """
        try:
            for audio in self.soup.find_all("audio"):
                for source in audio.find_all("source"):
                    yield(self.get_absolute_url(source["src"]))
        except Exception as exception:
            raise RuntimeError("failed to get <audio> URLs")

    def get_picture_tag_urls(self):
        """Get <picture> tag URLs.

        :returns: <picture> tag URL
        :rtype: str
        """
        try:
            for picture in self.soup.find_all("picture"):
                for source in picture.find_all("source"):
                    yield(self.get_absolute_url(source["srcset"]))
        except Exception as exception:
            raise RuntimeError("failed to get <picture> URLS")

    def archive(
            self,
            tags=("link", "script", "img", "video", "audio", "picture")
    ):
        """Archive OpenDACHS ticket.

        :param tuple tags: external resources
        """
        try:
            scraper = cfscrape.create_scraper()
            get_urls = {
                "link": self.get_link_tag_urls,
                "script": self.get_script_tag_urls,
                "img": self.get_img_tag_urls,
                "video": self.get_video_tag_urls,
                "audio": self.get_audio_tag_urls,
                "picture": self.get_picture_tag_urls
            }
            with warcio.capture_http.capture_http(self.ticket.archive):
                for tag in tags:
                    for url in get_urls[tag]():
                        scraper.get(url)
        except KeyError as exception:
            raise ValueError("unsupported tag") from exception
        except Exception as exception:
            raise RuntimeError(
                "failed to archive OpenDACHS ticket"
            ) from exception