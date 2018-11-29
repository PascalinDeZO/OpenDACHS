======
SQLite
======

The `sqlite` module is a wrapper around `sqlite3`. It's main functionality is to provide pre-defined SQL queries, so
that the same query does not have to be repeated several times over in the ticket management code. All in all, it's
a bit over-engineered, so simplifying it a bit could be in order. The module's configuration is in sqlite.ini.
Mainly, the database layout is configured with the help of the configuration file.

.. automodule:: src.sqlite
    :members: