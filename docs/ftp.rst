===
FTP
===

The `ftp` module is used to retrieve the JSON files from the OpenDACHS server handling user requests. The file retrieval
is done via FTPS. Upon retrieving a file, the original file on the OpenDACHS server is deleted. The content of the file
is written to a temporary file on the server executing `opendachs`. These temporary files are deleted as soon as they
are no longer used. The module's associated configuration is in the configuration file ftp.ini.

.. automodule:: src.ftp
    :members: