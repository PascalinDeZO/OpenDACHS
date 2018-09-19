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
:synopsis: API call.
"""


# standard library imports
import subprocess

# third party imports
# library specific imports


def api_call(args):
    """API call.

    :param list args: command-line arguments
    """
    try:
        args = [
            "docker", "exec", "-it", "webrecorder_app_1",
            "python3", "-m",  "webrecorder.od_webrecorder", *args
        ]
        child = subprocess.Popen(args, stderr=subprocess.PIPE)
        while True:
            returncode = child.poll()
            if returncode is None:
                continue
            else:
                break
        if child.returncode != 0:
            raise RuntimeError(
                "failed to call API\t : exit status {}".format(
                    child.returncode
                )
            )
    except RuntimeError:
        raise
    except Exception as exception:
        raise RuntimeError("failed to call API\t: {}".format(exception))
    return
