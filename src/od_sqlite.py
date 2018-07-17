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
:synopsis: SQLite interface.
"""


# standard library imports
import logging
import sqlite3

# third party imports
# library specific imports


class SQLiteClient(object):
    """OpenDACHS SQLite database.

    :ivar ConfigParser sqlite: SQLite configuration
    """

    def __init__(self, sqlite):
        """Initialize OpenDACHS SQLite database.

        :param ConfigParser sqlite: SQLite configuration
        """
        try:
            logger = logging.getLogger().getChild(self.__init__.__name__)
            self.sqlite = sqlite
        except Exception:
            logger.exception("failed to initialize OpenDACHS SQLite database")
            raise
        return

    def connect(self):
        """Connect to OpenDACHS SQLite database.

        :returns: connection
        :rtype: Connection
        """
        try:
            logger = logging.getLogger().getChild(self.connect.__name__)
            connection = sqlite3.connect(
                self.sqlite["SQLite"]["database"],
                detect_types=sqlite3.PARSE_COLNAMES
            )
            connection.row_factory = sqlite3.Row
        except Exception:
            logger.exception("failed to connect to OpenDACHS SQLite database")
            raise
        return connection

    def create_table(self):
        """Create table if not exists."""
        try:
            logger = logging.getLogger().getChild(self.create_table.__name__)
            connection = self.connect()
            sql = "CREATE TABLE IF NOT EXISTS {table} ({column_defs})"
            if "ticket" not in self.sqlite["column_defs"]:
                raise KeyError("'ticket' column is required")
            if "email" not in self.sqlite["column_defs"]:
                raise KeyError("'email' column is required")
            if "flag" not in self.sqlite["column_defs"]:
                raise KeyError("'flag' column is required")
            column_defs = ", ".join(
                k + " " + v
                for k, v in self.sqlite["column_defs"].items()
            )
            sql = sql.format(
                table=self.sqlite["SQLite"]["table"], column_defs=column_defs
            )
            connection.execute(sql)
            connection.commit()
            connection.close()
        except Exception as exception:
            logger.exception("failed to create table\t: %s", exception)
            raise
        return

    def insert(self, parameters):
        """Insert records.

        :param list parameters: parameters
        """
        try:
            logger = logging.getLogger().getChild(self.insert.__name__)
            connection = self.connect()
            sql = "INSERT INTO {table} VALUES ({columns})".format(
                table=self.sqlite["SQLite"]["table"],
                columns=", ".join(
                    "?" for _ in range(len(self.sqlite["column_defs"].items()))
                )
            )
            connection.executemany(sql, parameters)
            connection.commit()
            connection.close()
        except Exception:
            logger.exception("failed to insert records")
            raise
        return

    def select(self, parameters):
        """Select record.

        :param tuple parameters: parameters

        :returns: record
        :rtype: dict
        """
        try:
            logger = logging.getLogger().getChild(self.select.__name__)
            connection = self.connect()
            sql = "SELECT * FROM {table} WHERE {column} = ?".format(
                table=self.sqlite["SQLite"]["table"],
                column="ticket"
            )
            records = list(connection.execute(sql, parameters))
            assert len(records) <= 1, "non-unique primary key"
            record = dict(records[0]) if len(records) == 1 else {}
        except Exception:
            logger.exception("failed to select record")
            raise
        return record

    def update(self, parameters):
        """Update records.

        :param list parameters: parameters
        """
        try:
            logger = logging.getLogger().getChild(self.update.__name__)
            connection = self.connect()
            sql = "UPDATE {table} SET {column0} = ? WHERE {column1} = ?"
            sql = sql.format(
                table=self.sqlite["SQLite"]["table"],
                column0="flag",
                column1="ticket"
            )
            connection.executemany(sql, parameters)
            connection.commit()
            connection.close()
        except Exception as exception:
            logger.exception("failed to update records\t: %s", exception)
            raise
        return

    def delete(self, parameters):
        """Delete records.

        :param list parameters: parameters
        """
        try:
            logger = logging.getLogger().getChild(self.delete.__name__)
            connection = self.connect()
            sql = "DELETE FROM {table} WHERE {column} = ?".format(
                table=self.sqlite["SQLite"]["table"],
                column="ticket"
            )
            connection.executemany(sql, parameters)
            connection.commit()
            connection.close()
        except Exception as exception:
            logger.exception("failed to delete records\t: %s", exception)
            raise
        return
