=====
Email
=====

The `email` module is used to compose and send e-mails. Jinja2 templates are used to template the e-mail bodies. Some
of the functions take an argument `smtp`, a `ConfigParser` instance containing the relevant configuration, such as,
e.g., the e-mail server and its port, and the header fields.

.. automodule:: src.email
    :members: