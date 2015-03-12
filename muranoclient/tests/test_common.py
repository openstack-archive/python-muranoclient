# Copyright (c) 2015 Mirantis, Inc.
#
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

import StringIO
import tempfile

import mock
import requests
import testtools

from muranoclient.common import utils


class UtilsTest(testtools.TestCase):

    def test_file_object_from_file(self):
        f_obj = tempfile.NamedTemporaryFile(delete=True)
        new_f_obj = utils.File(f_obj).open()
        self.assertTrue(hasattr(new_f_obj, 'read'))

        new_f_obj = utils.File(f_obj.name).open()
        self.assertTrue(hasattr(new_f_obj, 'read'))

    def test_file_object_file_fails(self):
        f_obj = utils.File('')
        self.assertRaises(ValueError, f_obj.open)

    def test_file_object_url_fails(self):
        resp = requests.Response()
        resp.status_code = 400
        resp.raw = StringIO.StringIO("123")

        with mock.patch(
                'requests.get',
                mock.Mock(side_effect=lambda k, *args, **kwargs: resp)):
            f = utils.File("http://127.0.0.1")
            self.assertRaises(ValueError, f.open)

    def test_file_object_url(self):
        resp = requests.Response()
        resp.raw = StringIO.StringIO("123")
        resp.status_code = 200
        with mock.patch(
                'requests.get',
                mock.Mock(side_effect=lambda k, *args, **kwargs: resp)):
            new_f_obj = utils.File('http://127.0.0.1/').open()
            self.assertTrue(hasattr(new_f_obj, 'read'))

    def test_file_object_repo_fails(self):

        resp = requests.Response()
        resp.raw = StringIO.StringIO("123")
        resp.status_code = 400
        with mock.patch(
                'requests.get',
                mock.Mock(side_effect=lambda k, *args, **kwargs: resp)):
            self.assertRaises(
                ValueError, utils.Package.fromFile,
                utils.to_url('foo.bar.baz', base_url='http://127.0.0.1'))

    def test_no_repo_url_fails(self):
        self.assertRaises(ValueError, utils.to_url,
                          'foo.bar.baz', base_url='')

    def test_file_object_repo(self):
        resp = requests.Response()
        resp.raw = StringIO.StringIO("123")
        resp.status_code = 200
        with mock.patch(
                'requests.get',
                mock.Mock(side_effect=lambda k, *args, **kwargs: resp)):
            new_f_obj = utils.Package.fromFile(utils.to_url(
                'foo.bar.baz', base_url='http://')).file()
            self.assertTrue(hasattr(new_f_obj, 'read'))
