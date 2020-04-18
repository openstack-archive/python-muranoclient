# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import testtools
from unittest import mock

from muranoclient.common import exceptions as exc

HTML_MSG = """<html>
 <head>
  <title>403 Forbidden</title>
 </head>
 <body>
  <h1>403 Forbidden</h1>
  Access was denied to this resource.<br /><br />
 </body>
</html>"""


class TestHTTPExceptions(testtools.TestCase):
    def test_handles_json(self):
        """exc.from_response should not print JSON."""
        mock_resp = mock.Mock()
        mock_resp.status_code = 413
        mock_resp.json.return_value = {
            "overLimit": {
                "code": 413,
                "message": "OverLimit Retry...",
                "details": "Error Details...",
                "retryAt": "2015-08-31T21:21:06Z"
            }
        }
        mock_resp.headers = {
            "content-type": "application/json"
        }
        err = exc.from_response(mock_resp)
        self.assertIsInstance(err, exc.HTTPOverLimit)
        self.assertEqual("OverLimit Retry...", err.details)

    def test_handles_html(self):
        """exc.from_response should not print HTML."""
        mock_resp = mock.Mock()
        mock_resp.status_code = 403
        mock_resp.text = HTML_MSG
        mock_resp.headers = {
            "content-type": "text/html"
        }
        err = exc.from_response(mock_resp)
        self.assertIsInstance(err, exc.HTTPForbidden)
        self.assertEqual("403 Forbidden: Access was denied to this resource.",
                         err.details)
