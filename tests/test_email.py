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
:synopsis: E-mail composition and sending tests.
"""

# standard library imports
import shutil
import unittest

# third party imports
# library specific imports
import src.email


class TestEmail(unittest.TestCase):
    """Test email composition and sending."""

    def test_load_templates(self):
        """Load email templates.

        Expecting: templates 'accepted', 'confirmed', 'denied', 'error',
        'expired' and 'submitted'
        """
        templates = [
            "accepted", "confirmed", "denied", "error", "expired", "submitted"
        ]
        loader = src.email._load_templates(path="./../templates_sample")
        self.assertEqual(templates, loader.list_templates())

    def test_load_existing_template(self):
        """Load email template.

        Trying: template is one of 'accepted', 'confirmed', 'denied', 'error'
        'expired' and 'submitted'
        Expecting: template is loaded
        """
        templates = [
            "accepted", "confirmed", "denied", "error", "expired", "submitted"
        ]
        for template in templates:
            loaded_template = src.email.load_template(
                template, path="./../templates_sample"
            )
            self.assertEqual(template, loaded_template.name)

    def test_load_non_existing_template(self):
        """Load email template.

        Trying: template = 'foo'
        Expecting: RuntimeError
        """
        with self.assertRaises(RuntimeError):
            src.email.load_template("foo", path="./../templates_sample")