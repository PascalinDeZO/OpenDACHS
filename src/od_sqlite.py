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


def create_table(sqlite):
    """Create table if not exists.

    :param ConfigParser sqlite: SQLite configuration
    """
    try:
        logger = logging.getLogger().getChild(create_table.__name__)
        connection = sqlite3.connect(
            sqlite["SQLite"]["database"], detect_types=sqlite3.PARSE_COLNAMES
        )
        sql = "CREATE TABLE IF NOT EXISTS {table} ({column_defs})"
        column_defs = ", ".join(
            [
                #: ticket
                sqlite["SQLite"]["ticket"] + " TEXT PRIMARY KEY",
                #: e-mail address
                sqlite["SQLite"]["email"] + " TEXT",
                #: URL
                sqlite["SQLite"]["url"] + " TEXT",
                #: creator(s)
                sqlite["SQLite"]["creator"] + " BLOB",
                #: title
                sqlite["SQLite"]["title"] + " TEXT",
                #: publisher
                sqlite["SQLite"]["publisher"] + " TEXT",
                #: publication year
                sqlite["SQLite"]["publication_year"] + " TEXT",
                #: general resource type
                sqlite["SQLite"]["general_resource_type"] + " TEXT",
                #: resource type
                sqlite["SQLite"]["resource_type"] + " TEXT",
                #: flag
                sqlite["SQLite"]["flag"] + " TEXT",
                #: timestamp
                sqlite["SQLite"]["timestamp"] + " TIMESTAMP",
                #: WARC filename
                sqlite["SQLite"]["warc"] + " TEXT"
            ]
        )
        sql = sql.format(
            table=sqlite["SQLite"]["table"], column_defs=column_defs
        )
        connection.execute(sql)
        connection.commit()
        connection.close()
    except Exception:
        logger.exception("failed to create table")
        raise SystemExit
    return


def insert(sqlite, parameters):
    """Insert records.

    :param ConfigParser sqlite: SQLite configuration
    :param list parameters: parameters
    """
    try:
        logger = logging.getLogger().getChild(insert.__name__)
        connection = sqlite3.connect(
            sqlite["SQLite"]["database"],
            detect_types=sqlite3.PARSE_COLNAMES
        )
        sql = "INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        sql = sql.format(table=sqlite["SQLite"]["table"])
        connection.executemany(sql, parameters)
        connection.commit()
        connection.close()
    except Exception:
        logger.exception("failed to insert records")
        raise
    return


def update(sqlite, parameters):
    """Update records.

    :param ConfigParser sqlite: SQLite configuration
    :param list parameters: parameters
    """
    raise NotImplementedError


def delete(sqlite, parameters):
    """Delete records.

    :param ConfigParser sqlite: SQLite configuration
    :param list parameters: parameters
    """
    raise NotImplementedError


def execute(sqlite, sql):
    """Execute queries.

    :param ConfigParser sqlite: SQLite configuration
    :param dict sql: SQLite queries
    """
    try:
        logger = logging.getLogger().getChild(execute.__name__)
        for k, v in sql:
            if k == "insert":
                insert(sqlite, v)
            elif k == "update":
                update(sqlite, v)
            elif k == "delete":
                delete(sqlite, v)
    except Exception:
        logger.exception("failed to execute queries")
        raise
    return
