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
:synopsis: OpenDACHS ticket.
"""


# standard library imports
import json
import collections

# third party imports
# library specific imports


User = collections.namedTuple(
    "User", ["username", "role", "password", "email_addr"]
)


class Ticket(object):
    """OpenDACHS ticket.

    :ivar User user: Webrecorder user
    :ivar str archive WARC archive filename
    :ivar dict metadata: WARC archive metadata
    :ivar str flag: status flag
    """

    def __init__(self, id_, user, archive, metadata, flag, timestamp):
        """Initialize OpenDACHS ticket.

        :param str id_: ticket ID
        :param User user: Webrecorder user
        :param str archive: WARC archive filename
        :param dict metadata: WARC archive metadata
        :param str flag: status flag
        :param datetime timestamp: timestamp
        """
        try:
            self.id_ = id_
            self.user = user
            self.archive = archive
            self.metadata = metadata
            self._flag = flag
            self._timestamp = timestamp
        except Exception as exception:
            msg = "failed to initialize OpenDACHS ticket:{}".format(exception)
            raise RuntimeError(msg)
        return

    @property
    def flag(self):
        return self._flag

    @flag.setter
    def flag(self, value):
        self._flag = value
        return

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value
        return

    def get_row(self):
        """Get SQLite row.

        :returns: SQLite row
        :rtype: tuple
        """
        try:
            row = (
                self.id_,
                json.dumps(list(self.user)),
                self.archive,
                json.dumps(self.metadata),
                self.flag,
                self.timestamp
            )
        except Exception as exception:
            msg = "failed to get SQLite row:{}".format(exception)
            raise RuntimeError(msg)
        return row

    @classmethod
    def get_ticket(cls, row):
        """Get OpenDACHS ticket based on SQLite row.

        :param tuple row: SQLite row

        :returns: OpenDACHS ticket
        :rtype: Ticket
        """
        try:
            id_ = row[0]
            user = User(json.loads(row[1]))
            archive = row[2]
            metadata = json.loads(row[3])
            flag = row[4]
            timestamp = row[5]
            ticket = cls(id_, user, archive, metadata, flag, timestamp)
        except Exception as exception:
            msg = "failed to get OpenDACHS ticket:{}".format(exception)
            raise RuntimeError(msg)
        return ticket
