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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>


"""
:synopsis: Web scraping test cases.
"""

# standard library imports
import datetime
import unittest

# third party imports
import requests

# library specific imports
import src.ticket
import src.scraper


class TestScraper(unittest.TestCase):
    """Web scraper test cases base class.

    :ivar Ticket ticket: OpenDACHS ticket
    """
    def setUp(self):
        """Set Web scraper test cases up."""
        self.ticket = src.ticket.Ticket(
            "id_",
            src.ticket.User("username", "role", "password", "email_addr"),
            "archive.warc",
            {"url": ""},
            "flag",
            datetime.datetime.now()
        )


class TestGetBase(TestScraper):
    """Get base URL test cases."""

    def test_base_tag(self):
        """Get base URL.

        Trying: markup = "<base href='http://bar/baz'>"
        Excepting: base = http://bar/baz
        """
        response = requests.Response()
        response.status_code = 200
        response._content = "<base href='http://bar/baz'>"
        scraper = src.scraper.Scraper(self.ticket, response=response)
        self.assertEqual("http://bar/baz", scraper.base)

    def test_dir(self):
        """Get base URL.

        Trying: markup = empty string
        Expecting: base = http://fooi.com/bar/baz
        """
        self.ticket.metadata["url"] = "http://foo.com/bar/baz"
        request = requests.Request(url=self.ticket.metadata["url"])
        response = requests.Response()
        response.status_code = 200
        response.request = request
        response._content = ""
        scraper = src.scraper.Scraper(self.ticket, response=response)
        self.assertEqual("http://foo.com/bar/baz", scraper.base)

    def test_file(self):
        """Get base URL.

        Trying: markup = empty string
        Expecting: base = http://foo/bar
        """
        self.ticket.metadata["url"] = "http://foo.com/bar/baz.html"
        request = requests.Request(url=self.ticket.metadata["url"])
        response = requests.Response()
        response.status_code = 200
        response.request = request
        response._content = ""
        scraper = src.scraper.Scraper(self.ticket, response=response)
        self.assertEqual("http://foo.com/bar", scraper.base)


class TestGetAbsoluteURL(TestScraper):
    """Get absolute URL test cases.

    :ivar Scraper scraper: Web scraper
    """

    def setUp(self):
        """Set get absolute URL test cases up."""
        super().setUp()
        response = requests.Response()
        response.status_code = 200
        response._content = ""
        self.scraper = src.scraper.Scraper(self.ticket, response=response)

    def test_https(self):
        """Get absolute URL.

        Trying: relative = https://foo.html
        Expecting: absolute = relative
        """
        relative = "https://foo.html"
        absolute = self.scraper.get_absolute_url(relative)
        self.assertEqual(relative, absolute)

    def test_http(self):
        """Get absolute URL.

        Trying: relative = http://foo.html
        Expecting: absolute = relative
        """
        relative = "http://foo.html"
        absolute = self.scraper.get_absolute_url(relative)
        self.assertEqual(relative, absolute)

    def test_double_backslash_http(self):
        """Get absolute URL.

        Trying: base = http://bar, relative = //foo.html
        Expecting: absolute = http://foo.html
        """
        self.scraper.base = "http://bar"
        relative = "//foo.html"
        absolute = self.scraper.get_absolute_url(relative)
        self.assertEqual("http://foo.html", absolute)

    def test_double_backslash_https(self):
        """Get absolute URL.

        Trying: base = https://bar, relative = //foo.html
        Expecting: absolute = https://foo.html
        """
        self.scraper.base = "https://bar"
        relative = "//foo.html"
        absolute = self.scraper.get_absolute_url(relative)
        self.assertEqual("https://foo.html", absolute)

    def test_backslash(self):
        """Get absolute URL.

        Trying: base = http://foo.com/bar, relative = /baz.html
        Expecting: absolute = http://foo.com/baz.html
        """
        self.scraper.base = "http://foo.com/bar"
        relative = "/baz.html"
        absolute = self.scraper.get_absolute_url(relative)
        self.assertEqual("http://foo.com/baz.html", absolute)

    def test_no_backslash(self):
        """Get absolute URL.

        Trying: base = http://foo.com/bar, relative = baz.html
        Expecting: absolute = http://foo.com/bar/baz.html
        """
        self.scraper.base = "http://foo.com/bar"
        relative = "baz.html"
        absolute = self.scraper.get_absolute_url(relative)
        self.assertEqual("http://foo.com/bar/baz.html", absolute)


class TestGetURLs(TestScraper):
    """Get URLs test cases."""

    def setUp(self):
        """Set get URLs test cases up."""
        super().setUp()
        request = requests.Request(url=self.ticket.metadata["url"])
        self.response = requests.Response()
        self.response.status_code = 200
        self.response.request = request

    def test_link_tag_stylesheet(self):
        """Get <link> tag URLs.

        Trying: markup =
        <link rel='stylesheet' href='http://foo.css'>
        <link rel='stylesheet' href='http://bar.css'>
        Expecting: corresponding URLs
        """
        self.response._content = (
            "<link rel='stylesheet' href='http://foo.css'>"
            "<link rel='stylesheet' href='https://bar.css'>"
        )
        self.scraper = src.scraper.Scraper(self.ticket, response=self.response)
        urls = [url for url in self.scraper.get_link_tag_urls()]
        self.assertEqual(["http://foo.css", "https://bar.css"], urls)

    def test_link_tag_any_relationship(self):
        """Get <link> tag URLs.

        Trying: markup =
        <link rel='foo' href='http://foo.css'>
        <link rel='bar' href='http://bar.css'>
        Expecting: empty list
        """
        self.response._content = (
            "<link rel='foo' href='http://foo.css'>"
            "<link rel='bar' href='http://bar.css'>"
        )
        self.scraper = src.scraper.Scraper(self.ticket, response=self.response)
        urls = [url for url in self.scraper.get_link_tag_urls()]
        self.assertEqual([], urls)

    def test_script_tag_src(self):
        """Get <script> tag URLs.

        Trying: markup =
        <script src='http://foo.js'></script>
        <script src='http://bar.js'></script>
        Expecting: corresponding URLs
        """
        self.response._content = (
            "<script src='http://foo.js'></script>"
            "<script src='http://bar.js'></script>"
        )
        self.scraper = src.scraper.Scraper(self.ticket, response=self.response)
        urls = [url for url in self.scraper.get_script_tag_urls()]
        self.assertEqual(["http://foo.js", "http://bar.js"], urls)

    def test_script_tag_no_src(self):
        """Get <script> tag URLs.

        Trying: markup =
        <script>foo</script><script>bar</script>
        Expecting: empty list
        """
        self.response._content = "<script>foo</script><script>bar</script>"
        self.scraper = src.scraper.Scraper(self.ticket, response=self.response)
        urls = [url for url in self.scraper.get_script_tag_urls()]
        self.assertEqual([], urls)

    def test_img_tag(self):
        """Get <img> tag URLs.

        Trying: markup = <img src='http://foo.gif'><img src='http://bar.gif'>
        Expecting: corresponding URLs
        """
        self.response._content = (
            "<img src='http://foo.gif'>"
            "<img src='http://bar.gif'>"
        )
        self.scraper = src.scraper.Scraper(self.ticket, response=self.response)
        urls = [url for url in self.scraper.get_img_tag_urls()]
        self.assertEqual(["http://foo.gif", "http://bar.gif"], urls)

    def test_video_tag(self):
        """Get <video> tag URLs.

        Trying: markup =
        <video>
        <source src='http://foo.mp4'>
        <source src='http://bar.mp4'>
        </video>
        Expecting: corresponding URLs
        """
        self.response._content = (
            "<video>"
            "<source src='http://foo.mp4'>"
            "<source src='http://bar.mp4'>"
            "</video>"

        )
        self.scraper = src.scraper.Scraper(self.ticket, response=self.response)
        urls = [url for url in self.scraper.get_video_tag_urls()]
        self.assertEqual(["http://foo.mp4", "http://bar.mp4"], urls)

    def test_audio_tag(self):
        """Get <audio> tag URLs.

        Trying: markup =
        <audio>
        <source src='http://foo.mp3'>
        <source src='http://bar.mp3'>
        </audio>
        Expecting: corresponding URLs
        """
        self.response._content = (
            "<audio>"
            "<source src='http://foo.mp3'>"
            "<source src='http://bar.mp3'>"
            "</audio>"
        )
        self.scraper = src.scraper.Scraper(self.ticket, response=self.response)
        urls = [url for url in self.scraper.get_audio_tag_urls()]
        self.assertEqual(["http://foo.mp3", "http://bar.mp3"], urls)

    def test_picture_tag(self):
        """Get <picture> tag URLs.

        Trying: markup =
        <picture>
        <source srcset='foo.jpg'>
        <source srcset='bar.jpg'>
        </picture>
        Expecting: corresponding URLs
        """
        self.response._content = (
            "<picture>"
            "<source srcset='http://foo.jpg'>"
            "<source srcset='http://bar.jpg'>"
            "</picture>"
        )
        self.scraper = src.scraper.Scraper(self.ticket, response=self.response)
        urls = [url for url in self.scraper.get_picture_tag_urls()]
        self.assertEqual(["http://foo.jpg", "http://bar.jpg"], urls)