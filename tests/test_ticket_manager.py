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

# third party imports
# library specific imports
import src.ticket_manager


class TestTicketManager(unittest.TestCase):
    """OpenDACHS ticket manager test cases."""

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