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
:synopsis: SQLite interface.
"""


# standard library imports
import sqlite3

# third party imports
# library specific imports


class SQLiteClient(object):
    """OpenDACHS database client.

    :ivar ConfigParser sqlite: SQLite configuration
    """

    def __init__(self, sqlite):
        """Initialize OpenDACHS database client.

        :param ConfigParser sqlite: SQLite configuration
        """
        try:
            self.sqlite = sqlite
        except Exception as exception:
            msg = "failed to initialize OpenDACHS database client:{}".format(
                exception
            )
            raise RuntimeError(msg)
        return

    def connect(self):
        """Connect to OpenDACHS database.

        :returns: connection
        :rtype: Connection
        """
        try:
            connection = sqlite3.connect(
                self.sqlite["SQLite"]["database"],
                detect_types=sqlite3.PARSE_COLNAMES
            )
            connection.row_factory = sqlite3.Row
        except Exception as exception:
            msg = "failed to connect to OpenDACHS database:{}".format(
                exception
            )
            raise RuntimeError(msg)
        return connection

    def create_table(self):
        """Create table if not exists."""
        try:
            connection = self.connect()
            sql = "CREATE TABLE IF NOT EXISTS {table} {column_defs}"
            column_defs = ", ".join(
                "{} {}".format(k, v)
                for k, v in self.sqlite["column_defs"].items()
            )
            sql = sql.format(
                table=self.sqlite["SQLite"]["table"],
                column_defs=column_defs
            )
            connection.execute(sql)
            connection.commit()
            connection.close()
        except Exception as exception:
            msg = "failed to create table:{}".format(exception)
            raise RuntimeError(msg)
        return

    def insert(self, rows):
        """Insert rows.

        :param list rows: rows
        """
        try:
            connection = self.connect()
            sql = "INSERT INTO {table} VALUES {{columns}}".format(
                table=self.sqlite["SQLite"]["table"],
                columns=", ".join(
                    "?" for _ in range(len(self.sqlite["column_defs"]))
                )
            )
            connection.executemany(sql, rows)
            connection.commit()
            connection.close()
        except Exception as exception:
            msg = "failed to insert rows:{}".format(exception)
            raise RuntimeError(msg)
        return

    def select_rows(self, column="", parameters=()):
        """Select rows.

        :param str column: column
        :param tuple parameters: parameters

        :returns: rows
        :rtype: list
        """
        try:
            connection = self.connect()
            if column and parameters:
                sql = "SELECT * FROM {table} WHERE {column} = ?".format(
                    table=self.sqlite["SQLite"]["table"],
                    column=column
                )
                cursor = connection.execute(sql, parameters)
            elif column or parameters:
                msg = "either pass both column and parameters or neither"
                raise RuntimeError(msg)
            else:
                sql = "SELECT * FROM {table}".format(
                    table=self.sqlite["SQLite"]["table"]
                )
                cursor = connection.execute(sql)
            rows = [tuple(row) for row in cursor]
        except Exception as exception:
            msg = "failed to select rows:{}".format(exception)
            raise RuntimeError(msg)
        return rows

    def select_row(self, column, parameters):
        """Select row.

        :param str column: column
        :param tuple parameters: parameters

        :returns: row or None
        :rtype: tuple or None
        """
        try:
            rows = self.select_rows(column=column, parameters=parameters)
            if len(rows) > 1:
                msg = "query result is not unique"
                raise RuntimeError(msg)
            elif len(rows):
                row = None
            else:
                row = rows[0]
        except Exception as exception:
            msg = "failed to select row:{}".format(exception)
            raise RuntimeError(msg)
        return row

    def update_rows(self, column0, parameters, column1=""):
        """Update rows.

        :param str column0: column to be updated
        :param tuple parameters: parameters
        :param str column1: column WHERE clause

        :returns: rows (updated)
        :rtype: list
        """
        try:
            connection = self.connect()
            if column1:
                sql = "UPDATE {table} SET {column0} = ? WHERE {column1} = ?"
                sql = sql.format(
                    table=self.sqlite["SQLite"]["table"],
                    column0=column0,
                    column1=column1
                )
            else:
                sql = "UPDATE {table} SET {column0} = ?"
                sql = sql.format(
                    table=self.sqlite["SQLite"]["table"],
                    column0=column0
                )
            connection.executemany(sql, parameters)
            connection.commit()
            connection.close()
        except Exception as exception:
            msg = "failed to update rows:{}".format(exception)
            raise RuntimeError(msg)
        try:
            rows = self.select_rows(column=column1, parameters=parameters)
        except Exception as exception:
            msg = "failed to select updated rows:{}".format(exception)
            raise RuntimeError(msg)
        return rows

    def update_row(self, column0, column1, parameters):
        """Update row.

        :param str column0: column to be updated
        :param str column1: column WHERE clause
        :param tuple parameters: parameters

        :returns: row or None
        :rtype: tuple or None
        """
        try:
            rows = self.update_rows(column0, parameters, column1=column1)
            if len(rows) > 1:
                msg = "failed to select updated row:{}".format(
                    "query result is not unique"
                )
                raise RuntimeError(msg)
            elif len(rows) == 0:
                row = None
            else:
                row = rows[0]
        except Exception as exception:
            msg = "failed to update and/or select updated row:{}".format(
                exception
            )
            raise RuntimeError(msg)
        return row

    def delete(self, column, parameters):
        """Delete rows.

        :param tuple parameters: parameters
        """
        try:
            connection = self.connect()
            sql = "DELETE FROM {table} WHERE {column} = ?"
            sql = sql.format(
                table=self.sqlite["SQLite"]["table"],
                column=column
            )
            connection.executemany(sql, parameters)
            connection.commit()
            connection.close()
        except Exception as exception:
            msg = "failed to delete rows:{}".format(exception)
            raise RuntimeError(msg)
        return
