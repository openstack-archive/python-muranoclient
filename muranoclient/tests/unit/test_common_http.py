# -*- coding:utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket

import mock
import testtools

from muranoclient.common import exceptions as exc
from muranoclient.common import http
from muranoclient.tests.unit import fakes


@mock.patch('muranoclient.common.http.requests.request')
class HttpClientTest(testtools.TestCase):

    def test_http_raw_request(self, mock_request):
        headers = {'User-Agent': 'python-muranoclient'}
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                200, 'OK',
                {},
                '')

        client = http.HTTPClient('http://example.com:8082')
        resp = client.request('', 'GET')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('', ''.join([x for x in resp.content]))
        mock_request.assert_called_with('GET', 'http://example.com:8082',
                                        allow_redirects=False,
                                        headers=headers)

    def test_token_or_credentials(self, mock_request):
        # Record a 200
        fake200 = fakes.FakeHTTPResponse(
            200, 'OK',
            {},
            '')

        mock_request.side_effect = [fake200, fake200, fake200]

        # Replay, create client, assert
        client = http.HTTPClient('http://example.com:8082')
        resp = client.request('', 'GET')
        self.assertEqual(200, resp.status_code)

        client.username = 'user'
        client.password = 'pass'
        resp = client.request('', 'GET')
        self.assertEqual(200, resp.status_code)

        client.auth_token = 'abcd1234'
        resp = client.request('', 'GET')
        self.assertEqual(200, resp.status_code)

        # no token or credentials
        mock_request.assert_has_calls([
            mock.call('GET', 'http://example.com:8082',
                      allow_redirects=False,
                      headers={'User-Agent': 'python-muranoclient'}),
            mock.call('GET', 'http://example.com:8082',
                      allow_redirects=False,
                      headers={'User-Agent': 'python-muranoclient',
                               'X-Auth-Key': 'pass',
                               'X-Auth-User': 'user'}),
            mock.call('GET', 'http://example.com:8082',
                      allow_redirects=False,
                      headers={'User-Agent': 'python-muranoclient',
                               'X-Auth-Token': 'abcd1234'})
        ])

    def test_region_name(self, mock_request):
        # Record a 200
        fake200 = fakes.FakeHTTPResponse(
            200, 'OK',
            {},
            '')

        mock_request.return_value = fake200

        client = http.HTTPClient('http://example.com:8082')
        client.region_name = 'RegionOne'
        resp = client.request('', 'GET')
        self.assertEqual(200, resp.status_code)

        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082',
            allow_redirects=False,
            headers={'X-Region-Name': 'RegionOne',
                     'User-Agent': 'python-muranoclient'})

    def test_http_json_request(self, mock_request):
        # Record a 200
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')
        client = http.HTTPClient('http://example.com:8082')
        resp, body = client.json_request('', 'GET')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, body)

        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'})

    def test_http_json_request_argument_passed_to_requests(self, mock_request):
        """Check that we have sent the proper arguments to requests."""
        # Record a 200
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')

        client = http.HTTPClient('http://example.com:8082')
        client.verify_cert = True
        client.cert_file = 'RANDOM_CERT_FILE'
        client.key_file = 'RANDOM_KEY_FILE'
        client.auth_url = 'http://AUTH_URL'
        resp, body = client.json_request('', 'GET', data='text')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, body)

        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082',
            allow_redirects=False,
            cert=('RANDOM_CERT_FILE', 'RANDOM_KEY_FILE'),
            verify=True,
            data='"text"',
            headers={'Content-Type': 'application/json',
                     'X-Auth-Url': 'http://AUTH_URL',
                     'User-Agent': 'python-muranoclient'})

    def test_http_json_request_w_req_body(self, mock_request):
        # Record a 200
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')

        client = http.HTTPClient('http://example.com:8082')
        resp, body = client.json_request('', 'GET', data='test-body')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, body)
        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082',
            data='"test-body"',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'})

    def test_http_json_request_non_json_resp_cont_type(self, mock_request):
        # Record a 200
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'not/json'},
                '{}')

        client = http.HTTPClient('http://example.com:8082')
        resp, body = client.json_request('', 'GET', data='test-data')
        self.assertEqual(200, resp.status_code)
        self.assertIsNone(body)
        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082', data='"test-data"',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'})

    def test_http_json_request_invalid_json(self, mock_request):
        # Record a 200
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                'invalid-json')

        client = http.HTTPClient('http://example.com:8082')
        resp, body = client.json_request('', 'GET')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('invalid-json', body)
        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'})

    def test_http_manual_redirect_delete(self, mock_request):
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8082/foo/bar'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')]

        client = http.HTTPClient('http://example.com:8082/foo')
        resp, body = client.json_request('', 'DELETE')

        self.assertEqual(200, resp.status_code)
        mock_request.assert_has_calls([
            mock.call('DELETE', 'http://example.com:8082/foo',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'User-Agent': 'python-muranoclient'}),
            mock.call('DELETE', 'http://example.com:8082/foo/bar',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'User-Agent': 'python-muranoclient'})
        ])

    def test_http_manual_redirect_post(self, mock_request):
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8082/foo/bar'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')]

        client = http.HTTPClient('http://example.com:8082/foo')
        resp, body = client.json_request('', 'POST')

        self.assertEqual(200, resp.status_code)
        mock_request.assert_has_calls([
            mock.call('POST', 'http://example.com:8082/foo',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'User-Agent': 'python-muranoclient'}),
            mock.call('POST', 'http://example.com:8082/foo/bar',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'User-Agent': 'python-muranoclient'})
        ])

    def test_http_manual_redirect_put(self, mock_request):
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8082/foo/bar'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')]

        client = http.HTTPClient('http://example.com:8082/foo')
        resp, body = client.json_request('', 'PUT')

        self.assertEqual(200, resp.status_code)
        mock_request.assert_has_calls([
            mock.call('PUT', 'http://example.com:8082/foo',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'User-Agent': 'python-muranoclient'}),
            mock.call('PUT', 'http://example.com:8082/foo/bar',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'User-Agent': 'python-muranoclient'})
        ])

    def test_http_manual_redirect_prohibited(self, mock_request):
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8082/'},
                '')
        client = http.HTTPClient('http://example.com:8082/foo')
        self.assertRaises(exc.InvalidEndpoint,
                          client.json_request, '', 'DELETE')
        mock_request.assert_called_once_with(
            'DELETE', 'http://example.com:8082/foo',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'})

    def test_http_manual_redirect_error_without_location(self, mock_request):
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                302, 'Found',
                {},
                '')
        client = http.HTTPClient('http://example.com:8082/foo')
        self.assertRaises(exc.InvalidEndpoint,
                          client.json_request, '', 'DELETE')
        mock_request.assert_called_once_with(
            'DELETE', 'http://example.com:8082/foo',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'})

    def test_http_json_request_redirect(self, mock_request):
        # Record the 302
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8082'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')]

        client = http.HTTPClient('http://example.com:8082')
        resp, body = client.json_request('', 'GET')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, body)

        mock_request.assert_has_calls([
            mock.call('GET', 'http://example.com:8082',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'User-Agent': 'python-muranoclient'}),
            mock.call('GET', 'http://example.com:8082',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'User-Agent': 'python-muranoclient'})
        ])

    def test_http_404_json_request(self, mock_request):
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                404, 'Not Found', {'content-type': 'application/json'},
                '{}')

        client = http.HTTPClient('http://example.com:8082')
        e = self.assertRaises(exc.HTTPNotFound, client.json_request, '', 'GET')
        # Assert that the raised exception can be converted to string
        self.assertIsNotNone(str(e))
        # Record a 404
        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'})

    def test_http_300_json_request(self, mock_request):
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                300, 'OK', {'content-type': 'application/json'},
                '{}')
        client = http.HTTPClient('http://example.com:8082')
        e = self.assertRaises(
            exc.HTTPMultipleChoices, client.json_request, '', 'GET')
        # Assert that the raised exception can be converted to string
        self.assertIsNotNone(str(e))

        # Record a 300
        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'})

    def test_fake_json_request(self, mock_request):
        headers = {'User-Agent': 'python-muranoclient'}
        mock_request.side_effect = [socket.gaierror]

        client = http.HTTPClient('fake://example.com:8082')
        self.assertRaises(exc.InvalidEndpoint,
                          client.request, "/", "GET")
        mock_request.assert_called_once_with('GET', 'fake://example.com:8082/',
                                             allow_redirects=False,
                                             headers=headers)

    def test_http_request_socket_error(self, mock_request):
        headers = {'User-Agent': 'python-muranoclient'}
        mock_request.side_effect = [socket.gaierror]

        client = http.HTTPClient('http://example.com:8082')
        self.assertRaises(exc.InvalidEndpoint,
                          client.request, "/", "GET")
        mock_request.assert_called_once_with('GET', 'http://example.com:8082/',
                                             allow_redirects=False,
                                             headers=headers)

    def test_http_request_socket_timeout(self, mock_request):
        headers = {'User-Agent': 'python-muranoclient'}
        mock_request.side_effect = [socket.timeout]

        client = http.HTTPClient('http://example.com:8082')
        self.assertRaises(exc.CommunicationError,
                          client.request, "/", "GET")
        mock_request.assert_called_once_with('GET', 'http://example.com:8082/',
                                             allow_redirects=False,
                                             headers=headers)

    def test_http_request_specify_timeout(self, mock_request):
        mock_request.return_value = \
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')

        client = http.HTTPClient('http://example.com:8082', timeout='123')
        resp, body = client.json_request('', 'GET')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, body)
        mock_request.assert_called_once_with(
            'GET', 'http://example.com:8082',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'python-muranoclient'},
            timeout=float(123))

    def test_get_system_ca_file(self, mock_request):
        chosen = '/etc/ssl/certs/ca-certificates.crt'
        with mock.patch('os.path.exists') as mock_os:
            mock_os.return_value = chosen

            ca = http.get_system_ca_file()
            self.assertEqual(chosen, ca)

            mock_os.assert_called_once_with(chosen)

    def test_insecure_verify_cert_None(self, mock_request):
        client = http.HTTPClient('https://foo', insecure=True)
        self.assertFalse(client.verify_cert)

    def test_passed_cert_to_verify_cert(self, mock_request):
        client = http.HTTPClient('https://foo', cacert="NOWHERE")
        self.assertEqual("NOWHERE", client.verify_cert)

        with mock.patch('muranoclient.common.http.get_system_ca_file') as gsf:
            gsf.return_value = "SOMEWHERE"
            client = http.HTTPClient('https://foo')
            self.assertEqual("SOMEWHERE", client.verify_cert)

#    def test_curl_log_i18n_headers(self, mock_request):
#        self.m.StubOutWithMock(logging.Logger, 'debug')
#        kwargs = {'headers': {'Key': b'foo\xe3\x8a\x8e'}}
#
#        mock_logging_debug = logging.Logger.debug(
#            u"curl -i -X GET -H 'Key: foo㊎' http://somewhere"
#        )
#        mock_logging_debug.AndReturn(None)
#
#        self.m.ReplayAll()
#
#        client = http.HTTPClient('http://somewhere')
#        client.log_curl_request('', "GET", kwargs=kwargs)
#
#        self.m.VerifyAll()
