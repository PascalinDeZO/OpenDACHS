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
    """OpenDACHS ticket manager test cases base class.

    :ivar TicketManager ticket_manager: OpenDACHS ticket manager
    """

    def setUp(self):
        """Set test cases up."""
        ftp = configparser.ConfigParser()
        ftp.read_dict(
            {
                "FTP": {"host": "", "user": "", "passwd": ""},
                "cmd": {"RETR": ""}
            }
        )
        smtp = configparser.ConfigParser()
        smtp.read_dict(
            {
                "SMTP": {"host": "", "port": ""},
                "header_fields": {"from": "", "reply_to": ""}
            }
        )
        sqlite = configparser.ConfigParser()
        sqlite.read_dict(
            {
                "SQLite": {
                    "database": ":memory:",
                    "table": "tickets"
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


class TestGenerateUser(TestTicketManager):
    """Webrecorder user generation test cases."""

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


class TestGenerateTicket(TestTicketManager):
    """OpenDACHS ticket generation test cases."""

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