#    OpenDACHS 1.0
#    Copyright (C) 2018  Carine Dengler, Universität Heidelberg
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
:synopsis: OpenDACHS ticket manager test cases.
"""

# standard library imports
import unittest
import random
import configparser

# third party imports
import requests

# library specific imports
import src.ticket_manager


class TestTicketManager(unittest.TestCase):
    """OpenDACHS ticket manager test cases.

    :ivar TicketManager ticket_manager: OpenDACHS ticket manager
    """

    def setUp(self):
        """Set test cases up."""
        ftp = configparser.ConfigParser()
        ftp.read_dict({})
        smtp = configparser.ConfigParser()
        smtp.read_dict({})
        sqlite = configparser.ConfigParser()
        sqlite.read_dict(
            {
                "SQLite": {
                    "database": ":memory:",
                    "table": "tickets",
                },
                "column_defs": {
                    "ticket": "TEXT PRIMARY KEY",
                    "user": "TEXT",
                    "archive": "TEXT",
                    "metadata": "TEXT",
                    "flag": "TEXT",
                    "timestamp": "TIMESTAMP"
                }
            }
        )
        self.ticket_manager = src.ticket_manager.TicketManager(
            ftp, smtp, sqlite
        )

    def test_generate_username_default(self):
        """Generate Webrecorder username.

        Trying: default length value
        Expecting: [A-Za-z0-9]{8} matches username
        """
        username = src.ticket_manager.TicketManager.generate_username()
        self.assertRegex(username, r"[A-Za-z0-9]{8}")

    def test_generate_username_valid_length(self):
        """Generate Webrecorder username.

        Trying: 1 <= length <= 100
        Expecting: [A-Za-z0-9]{length} matches username
        """
        length = random.randint(1, 100)
        username = src.ticket_manager.TicketManager.generate_username(
            length=length
        )
        self.assertRegex(username, r"[A-Za-z0-9]{{{}}}".format(length))

    def test_generate_username_invalid_length(self):
        """Generate Webrecorder username.

        Trying: -100 <= length <= 0
        Expecting: RuntimeError
        """
        length = random.randint(-100, 0)
        with self.assertRaises(RuntimeError):
            username = src.ticket_manager.TicketManager.generate_username(
                length=length
            )

    def test_generate_password(self):
        """Generate Webrecorder password.

        Trying: default length value
        Expecting: [A-Za-z0-9]{16} matches password
        """
        password = src.ticket_manager.TicketManager.generate_password()
        self.assertRegex(password, r"[A-Za-z0-9]{16}")

    def test_generate_password_valid_length(self):
        """Generate Webrecorder password.

        Trying: 1 <= length <= 100
        Expecting: [A-Za-z0-9]{length} matches username
        """
        length = random.randint(1, 100)
        password = src.ticket_manager.TicketManager.generate_password(
            length=length
        )
        self.assertRegex(password, r"[A-Za-z0-9]{{{}}}".format(length))

    def test_generate_password_invalid_length(self):
        """Generate Webrecorder password.

        Trying: -100 <= length <= 0
        Expecting: RuntimeError
        """
        length = random.randint(-100, 0)
        with self.assertRaises(RuntimeError):
            password = src.ticket_manager.TicketManager.generate_password(
                length=length
            )

    def test_get_url_https(self):
        """Get absolute src URL.

        Trying: url = http://foo.com/bar, base_src_url = https://baz.com
        Expecting: absolute src URL = src
        """
        url = "http://foo.com/bar"
        base_src_url = "https://baz.com"
        abs_src_url = src.ticket_manager.TicketManager._get_url(
            url, base_src_url
        )
        self.assertEqual(base_src_url, abs_src_url)

    def test_get_url_http(self):
        """Get absolute src URL.

        Trying: url = http://foo.com/bar, base_src_url = http://baz.com
        Expecting: absolute src URL = src
        """
        url = "http://foo.com/bar"
        base_src_url = "http://baz.com"
        abs_src_url = src.ticket_manager.TicketManager._get_url(
            url, base_src_url
        )
        self.assertEqual(base_src_url, abs_src_url)

    def test_get_url_backslash(self):
        """Get absolute src URL.

        Trying: url = http://foo.com/bar, base_src_url = /baz
        Expecting: absolute src URL = http://foo.com + base_src_url
        """
        url = "http://foo.com/bar"
        base_src_url = "/baz"
        abs_src_url = src.ticket_manager.TicketManager._get_url(
            url, base_src_url
        )
        self.assertEqual("http://foo.com"+base_src_url, abs_src_url)

    def test_get_url_without_backslash(self):
        """Get absolute src URL.

        Trying: url = http://foo.com/bar, base_src_url = baz
        Expecting: absolute src URL = url + / + base_src_url
        """
        url = "http://foo.com/bar"
        base_src_url = "baz"
        abs_src_url = src.ticket_manager.TicketManager._get_url(
            url, base_src_url
        )
        self.assertEqual(url+"/"+base_src_url, abs_src_url)

    def test_get_img_urls(self):
        """Archive images.

        Trying: url = http://foo.com/bar and src one of
        https://baz.com, http://baz.com, /baz and baz
        Expecting: corresponding absolute src URLs
        """
        src = ["https://baz.com", "http://baz.com", "/baz", "baz"]
        abs_src = [
            src[0],
            src[1],
            "http://foo.com"+src[2],
            "http://foo.com/bar/"+src[3]
        ]
        img = "".join(
            "<img src='{src}' alt='alt'>".format(src=value)
            for value in src
        )
        request = requests.Request(url="http://foo.com/bar")
        response = requests.Response()
        response._content = "<html>{img}</html>".format(img=img)
        response.request = request
        self.assertEqual(
            abs_src,
            list(self.ticket_manager._get_image_urls(response))
        )

    def test_get_media_urls(self):
        """Get media URLs.

        Trying: url = http://foo.com/bar and source one of
        <source src='baz'> and <source srcset='baz'>
        Expecting: corresponding absolute src URLs
        """
        url = "http://foo.com/bar"
        content = "".join(
            ["<source src='baz'>", "<source srcset='baz'>"]
        )
        abs_src = url+"/baz"
        request = requests.Request(url=url)
        response = requests.Response()
        response._content = content
        response.request = request
        self.assertEqual(
            [abs_src, abs_src],
            list(self.ticket_manager._get_media_urls(response))
        )

    def test_initialize_user(self):
        """Initialize Webrecorder user.

        Trying: email_addr = foo@bar.com
        Expecting: [A-Za-z0-9]{8} matches username, role = archivist,
        [A-Za-z0-9]{16} matches password and email_addr = foo@bar.com
        """
        email_addr = "foo@bar.com"
        user = self.ticket_manager._initialize_user({"email": email_addr})
        self.assertRegex(user.username, r"[A-Za-z0-9]{8}")
        self.assertEqual("archivist", user.role)
        self.assertRegex(user.password, r"[A-Za-z0-9]{16}")
        self.assertEqual(email_addr, user.email_addr)

    def test_initialize_ticket(self):
        """Initialize OpenDACHS ticket.

        Trying: ticket = ABCabc123, email_addr = foo@bar.com,
        foo = 1, bar = 2, baz = 3 and flag = flag
        Expecting: corresponding OpenDACHS ticket
        """
        data = {
            "ticket": "ABCabc123",
            "email": "foo@bar.com",
            "foo": 1,
            "bar": 2,
            "baz": 3,
            "flag": "flag"
        }
        archive = "tmp/warcs/{ticket}.warc".format(ticket=data["ticket"])
        ticket = self.ticket_manager._initialize_ticket(data)
        self.assertEqual(data["ticket"], ticket.id_)
        self.assertEqual(data["email"], ticket.user.email_addr)
        self.assertEqual(archive, ticket.archive)
        self.assertEqual(
            {
                "foo": data["foo"],
                "bar": data["bar"],
                "baz": data["baz"]
            }, ticket.metadata
        )
        self.assertEqual(data["flag"], ticket.flag)
        self.assertTrue(hasattr(ticket, "timestamp"))