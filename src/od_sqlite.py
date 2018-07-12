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
                sqlite["SQLite"]["ticket"] + " TEXT PRIMARY KEY",   #: ticket
                sqlite["SQLite"]["email"] + " TEXT",    #: e-mail address
                sqlite["SQLite"]["url"] + " TEXT",      #: URL
                sqlite["SQLite"]["creator"] + " BLOB",  #: creator(s)
                sqlite["SQLite"]["title"] + " TEXT",    #: title
                sqlite["SQLite"]["publisher"] + " TEXT",    #: publisher
                #: publication year
                sqlite["SQLite"]["publication_year"] + " TEXT",
                #: general resource type
                sqlite["SQLite"]["general_resource_type"] + " TEXT",
                #: resource type
                sqlite["SQLite"]["resource_type"] + " TEXT",
                sqlite["SQLite"]["flag"] + " TEXT",         #: flag
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


def insert_rows(sqlite, rows):
    """Insert rows.

    :param ConfigParser sqlite: SQLite configuration
    :param list rows: rows
    """
    try:
        logger = logging.getLogger().getChild(insert_rows.__name__)
        connection = sqlite3.connect(
            sqlite["SQLite"]["database"],
            detect_types=sqlite3.PARSE_COLNAMES
        )
        sql = "INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        sql = sql.format(table=sqlite["SQLite"]["table"])
        connection.executemany(sql, rows)
        connection.commit()
        connection.close()
    except Exception:
        logger.exception("failed to insert rows")
        raise
    return
