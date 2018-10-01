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
:synopsis: OpenDACHS ticket tests.
"""

# standard library imports
import unittest
import datetime
import json

# third party imports
# library specific imports
import src.ticket


class TestTicket(unittest.TestCase):
    """OpenDACHS ticket tests."""

    @classmethod
    def setUpClass(cls):
        """Set test case up."""
        user = src.ticket.User("username", "role", "password", "email_addr")
        timestamp = datetime.datetime.now()
        cls.ticket = src.ticket.Ticket(
            "id_", user, "archive", {}, "flag", timestamp
        )
        return

    def test_get_ticket_00(self):
        """Test method to get OpenDACHS ticket based on SQLite row."""
        row = (
            self.ticket.id_,
            json.dumps(list(self.ticket.user)),
            self.ticket.archive,
            json.dumps(self.ticket.metadata),
            self.ticket.flag,
            self.ticket.timestamp
        )
        ticket = self.ticket.get_ticket(row)
        self.assertEqual(self.ticket.id_, ticket.id_)
        self.assertEqual(self.ticket.user, ticket.user)
        self.assertEqual(self.ticket.archive, ticket.archive)
        self.assertEqual(self.ticket.metadata, ticket.metadata)
        self.assertEqual(self.ticket.flag, ticket.flag)
        self.assertEqual(self.ticket.timestamp, ticket.timestamp)
        return

    def test_get_json_00(self):
        """Test method to get JSON formatted string."""
        json_string = self.ticket.get_json()
        python_obj = json.loads(json_string)
        self.assertEqual(python_obj["id"], self.ticket.id_)
        self.assertEqual(python_obj["user"], list(self.ticket.user))
        self.assertEqual(python_obj["archive"], self.ticket.archive)
        self.assertEqual(python_obj["metadata"], {})
        self.assertEqual(python_obj["flag"], self.ticket.flag)
        self.assertEqual(
            python_obj["timestamp"], self.ticket.timestamp.isoformat()
        )
        return