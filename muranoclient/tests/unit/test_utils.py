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

import io
import json
import os.path
import tempfile
from unittest import mock
import zipfile

import requests
import requests_mock
import testtools
import yaml

from muranoclient.common import utils


class FileTest(testtools.TestCase):

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
        resp.raw = io.BytesIO(b"123")

        with mock.patch(
                'requests.get',
                mock.Mock(side_effect=lambda k, *args, **kwargs: resp)):
            f = utils.File("http://127.0.0.1")
            self.assertRaises(ValueError, f.open)

    def test_file_object_url(self):
        resp = requests.Response()
        resp.raw = io.BytesIO(b"123")
        resp.status_code = 200
        with mock.patch(
                'requests.get',
                mock.Mock(side_effect=lambda k, *args, **kwargs: resp)):
            new_f_obj = utils.File('http://127.0.0.1/').open()
            self.assertTrue(hasattr(new_f_obj, 'read'))


def make_pkg(manifest_override, image_dicts=None):
    manifest = {
        'Author': '',
        'Classes': {'foo': 'foo.yaml'},
        'Description': '',
        'Format': 1.0,
        'FullName': 'org.foo',
        'Name': 'Apache HTTP Server',
        'Type': 'Application'}
    manifest.update(manifest_override)
    file_obj = io.BytesIO()
    zfile = zipfile.ZipFile(file_obj, "a")
    zfile.writestr('manifest.yaml', yaml.dump(manifest))
    zfile.writestr('Classes/foo.yaml', yaml.dump({}))
    if image_dicts:
        images_list = []
        default_image_spec = {
            'ContainerFormat': 'bare',
            'DiskFormat': 'qcow2',
            'Name': '',
        }
        for image_dict in image_dicts:
            image_spec = default_image_spec.copy()
            image_spec.update(image_dict)
            images_list.append(image_spec)
        images = {'Images': images_list, }
        zfile.writestr('images.lst', yaml.dump(images))
    zfile.close()
    file_obj.seek(0)
    return file_obj


class PackageTest(testtools.TestCase):
    base_url = "http://127.0.0.1"

    @requests_mock.mock()
    def test_from_location_local_file(self, m):
        temp = tempfile.NamedTemporaryFile()
        pkg = make_pkg({'FullName': 'single_app'})

        temp.write(pkg.read())
        temp.flush()
        path, name = os.path.split(temp.name)

        # ensure we do not go to base url
        m.get(self.base_url + '/apps/{0}.zip'.format(name), status_code=404)

        self.assertEqual('single_app', utils.Package.from_location(
            name=name, base_url=self.base_url,
            path=path,
        ).manifest['FullName'])

    def test_package_from_directory(self):
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            "fixture_data/empty-app")
        pkg = utils.Package(utils.File(path))
        self.assertEqual('empty', pkg.manifest['FullName'])
        pkg = utils.Package.from_location('', path=path)
        self.assertEqual('empty', pkg.manifest['FullName'])

    @requests_mock.mock()
    def test_from_location_url(self, m):
        """Test that url overrides name specification."""

        pkg = make_pkg({'FullName': 'single_app'})
        m.get('http://127.0.0.2/apps/single_app.zip', body=pkg)
        m.get(self.base_url + '/apps/single_app.zip', status_code=404)

        self.assertEqual('single_app', utils.Package.from_location(
            name='single_app', base_url=self.base_url,
            url="http://127.0.0.2/apps/single_app.zip",
        ).manifest['FullName'])

    @requests_mock.mock()
    def test_from_location(self, m):
        """Test from location url requesting mechanism."""
        pkg = make_pkg({'FullName': 'single_app'})
        pkg_ver = make_pkg({'FullName': 'single_app'})
        m.get(self.base_url + '/apps/single_app.zip', body=pkg)
        m.get(self.base_url + '/apps/single_app.1.0.zip', body=pkg_ver)
        m.get(self.base_url + '/apps/single_app.2.0.zip', status_code=404)

        self.assertEqual('single_app', utils.Package.from_location(
            name='single_app', base_url=self.base_url).manifest['FullName'])

        self.assertEqual('single_app', utils.Package.from_location(
            name='single_app',
            version='1.0',
            base_url=self.base_url).manifest['FullName'])
        self.assertRaises(
            ValueError,
            utils.Package.from_location,
            name='single_app',
            version='2.0',
            base_url=self.base_url)

    def test_no_requirements(self):
        pkg = make_pkg({'FullName': 'single_app'})
        app = utils.Package.fromFile(pkg)
        reqs = app.requirements(base_url=self.base_url)
        self.assertEqual({'single_app': app}, reqs)

    @requests_mock.mock()
    def test_requirements(self, m):
        """Test that dependencies are parsed correctly."""

        pkg3 = make_pkg({'FullName': 'dep_of_dep'})
        pkg2 = make_pkg({'FullName': 'dep_app', 'Require': {
            'dep_of_dep': "1.0"}, })
        pkg1 = make_pkg({'FullName': 'main_app', 'Require': {
            'dep_app': None}, })

        m.get(self.base_url + '/apps/main_app.zip', body=pkg1)
        m.get(self.base_url + '/apps/dep_app.zip', body=pkg2)
        m.get(self.base_url + '/apps/dep_of_dep.1.0.zip', body=pkg3)
        app = utils.Package.fromFile(pkg1)
        reqs = app.requirements(base_url=self.base_url)

        self.assertEqual(
            {'main_app': app, 'dep_app': mock.ANY, 'dep_of_dep': mock.ANY},
            reqs)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_requirements_order(self, from_file):
        """Test that dependencies are parsed in correct order."""

        pkg5 = make_pkg({'FullName': 'd4', })
        pkg4 = make_pkg({'FullName': 'd3', 'Require': {'d4': None}, })
        pkg3 = make_pkg({'FullName': 'd2', 'Require': {'d3': None}, })
        pkg2 = make_pkg({'FullName': 'd1', 'Require': {'d3': None}, })
        pkg1 = make_pkg({'FullName': 'M', 'Require': {'d1': None,
                                                      'd2': None,
                                                      'd4': None}, })

        def side_effect(name):
            if 'M' in name:
                return utils.Package(utils.File(pkg1))
            if 'd1' in name:
                return utils.Package(utils.File(pkg2))
            if 'd2' in name:
                return utils.Package(utils.File(pkg3))
            if 'd3' in name:
                return utils.Package(utils.File(pkg4))
            if 'd4' in name:
                return utils.Package(utils.File(pkg5))

        from_file.side_effect = side_effect
        app = from_file('M')
        reqs = app.requirements(base_url=self.base_url)

        def key_position(key):
            keys = list(iter(reqs.keys()))
            return keys.index(key)

        self.assertTrue(
            key_position('d4') < key_position('d3') and
            key_position('d4') < key_position('M') and
            key_position('d3') < key_position('d1') and
            key_position('d3') < key_position('d2') < key_position('M')
        )

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_requirements_order2(self, from_file):
        """Test that dependencies are parsed in correct order."""

        pkg5 = make_pkg({'FullName': 'd4', 'Require': {'d6': None}, })
        pkg4 = make_pkg({'FullName': 'd3', 'Require': {'d4': None}, })
        pkg3 = make_pkg({'FullName': 'd1', 'Require': {'d3': None,
                                                       'd7': None}, })
        pkg2 = make_pkg({'FullName': 'd2', 'Require': {'d3': None}, })
        pkg6 = make_pkg({'FullName': 'd6', })
        pkg7 = make_pkg({'FullName': 'd7', 'Require': {'d8': None}, })
        pkg8 = make_pkg({'FullName': 'd8', })

        pkg1 = make_pkg({'FullName': 'M', 'Require': {'d1': None,
                                                      'd2': None,
                                                      'd4': None, }, })

        def side_effect(name):
            if 'M' in name:
                return utils.Package(utils.File(pkg1))
            if 'd1' in name:
                return utils.Package(utils.File(pkg2))
            if 'd2' in name:
                return utils.Package(utils.File(pkg3))
            if 'd3' in name:
                return utils.Package(utils.File(pkg4))
            if 'd4' in name:
                return utils.Package(utils.File(pkg5))
            if 'd6' in name:
                return utils.Package(utils.File(pkg6))
            if 'd7' in name:
                return utils.Package(utils.File(pkg7))
            if 'd8' in name:
                return utils.Package(utils.File(pkg8))

        from_file.side_effect = side_effect
        app = from_file('M')
        reqs = app.requirements(base_url=self.base_url)

        def key_position(key):
            keys = list(iter(reqs.keys()))
            return keys.index(key)

        self.assertTrue(
            key_position('d6') < key_position('d4') <
            key_position('d3') < key_position('d1') and
            key_position('d3') < key_position('d2') and
            key_position('d1') < key_position('M') and
            key_position('d2') < key_position('M') and
            key_position('d8') < key_position('d7') < key_position('d1')
        )

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_cyclic_requirements(self, from_file):
        """Test that a cyclic dependency would be handled correctly."""
        pkg3 = make_pkg({'FullName': 'dep_of_dep', 'Require': {
            'main_app': None, 'dep_app': None}, })
        pkg2 = make_pkg({'FullName': 'dep_app', 'Require': {
            'dep_of_dep': None, 'main_app': None}, })
        pkg1 = make_pkg({'FullName': 'main_app', 'Require': {
            'dep_app': None, 'dep_of_dep': None}, })

        def side_effect(name):
            if 'main_app' in name:
                return utils.Package(utils.File(pkg1))
            if 'dep_app' in name:
                return utils.Package(utils.File(pkg2))
            if 'dep_of_dep' in name:
                return utils.Package(utils.File(pkg3))

        from_file.side_effect = side_effect
        app = from_file('main_app')
        reqs = app.requirements(base_url=self.base_url)

        self.assertEqual(
            {'main_app': app, 'dep_app': mock.ANY, 'dep_of_dep': mock.ANY},
            reqs)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_order_with_cyclic_requirements2(self, from_file):
        """Test that dependencies are parsed in correct order."""

        pkg6 = make_pkg({'FullName': 'd5', 'Require': {'d6': None}, })
        pkg7 = make_pkg({'FullName': 'd6', })
        pkg5 = make_pkg({'FullName': 'd4', 'Require': {'d3': None,
                                                       'd5': None}})
        pkg4 = make_pkg({'FullName': 'd3', 'Require': {'d4': None}, })
        pkg3 = make_pkg({'FullName': 'd2', 'Require': {'d1': None,
                                                       'd5': None,
                                                       'd6': None}, })
        pkg2 = make_pkg({'FullName': 'd1', 'Require': {'d2': None}, })
        pkg1 = make_pkg({'FullName': 'M', 'Require': {'d1': None,
                                                      'd3': None}, })

        def side_effect(name):
            if 'M' in name:
                return utils.Package(utils.File(pkg1))
            if 'd1' in name:
                return utils.Package(utils.File(pkg2))
            if 'd2' in name:
                return utils.Package(utils.File(pkg3))
            if 'd3' in name:
                return utils.Package(utils.File(pkg4))
            if 'd4' in name:
                return utils.Package(utils.File(pkg5))
            if 'd5' in name:
                return utils.Package(utils.File(pkg6))
            if 'd6' in name:
                return utils.Package(utils.File(pkg7))

        from_file.side_effect = side_effect
        app = from_file('M')
        reqs = app.requirements(base_url=self.base_url)

        def key_position(key):
            keys = list(iter(reqs.keys()))
            return keys.index(key)

        self.assertTrue(
            key_position('d5') < key_position('d4') and
            key_position('d5') < key_position('d2') and
            key_position('d5') < key_position('d3') < key_position('M') and
            key_position('d5') < key_position('d1') < key_position('M')
        )

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_order_with_cyclic_requirements3(self, from_file):
        """Test that dependencies are parsed in correct order."""

        pkg5 = make_pkg({'FullName': 'd4', })
        pkg4 = make_pkg({'FullName': 'd3', 'Require': {'M': None}, })
        pkg3 = make_pkg({'FullName': 'd2', 'Require': {'d3': None,
                                                       'd4': None}, })
        pkg2 = make_pkg({'FullName': 'd1', 'Require': {'d2': None}, })
        pkg1 = make_pkg({'FullName': 'M', 'Require': {'d1': None}, })

        def side_effect(name):
            if 'M' in name:
                return utils.Package(utils.File(pkg1))
            if 'd1' in name:
                return utils.Package(utils.File(pkg2))
            if 'd2' in name:
                return utils.Package(utils.File(pkg3))
            if 'd3' in name:
                return utils.Package(utils.File(pkg4))
            if 'd4' in name:
                return utils.Package(utils.File(pkg5))

        from_file.side_effect = side_effect
        app = from_file('M')
        reqs = app.requirements(base_url=self.base_url)

        def key_position(key):
            keys = list(iter(reqs.keys()))
            return keys.index(key)

        self.assertTrue(
            key_position('d4') < key_position('M') and
            key_position('d4') < key_position('d1') and
            key_position('d4') < key_position('d2') and
            key_position('d4') < key_position('d3')
        )

    def test_images(self):
        pkg = make_pkg({})
        app = utils.Package.fromFile(pkg)
        self.assertEqual([], app.images())

        pkg = make_pkg(
            {}, [{'Name': 'test.qcow2'}, {'Name': 'test2.qcow2'}])
        app = utils.Package.fromFile(pkg)
        self.assertEqual(
            set(['test.qcow2', 'test2.qcow2']),
            set([img['Name'] for img in app.images()]))

    def test_file_object_repo_fails(self):
        resp = requests.Response()
        resp.raw = io.BytesIO(b"123")
        resp.status_code = 400
        with mock.patch(
                'requests.get',
                mock.Mock(side_effect=lambda k, *args, **kwargs: resp)):
            self.assertRaises(
                ValueError, utils.Package.from_location,
                name='foo.bar.baz', base_url='http://127.0.0.1')

    def test_no_repo_url_fails(self):
        self.assertRaises(ValueError, utils.Package.from_location,
                          name='foo.bar.baz', base_url='')

    @mock.patch.object(utils.Package, 'validate')
    def test_file_object_repo(self, m_validate):
        resp = requests.Response()
        resp.raw = io.BytesIO(b"123")
        resp.status_code = 200
        m_validate.return_value = None
        with mock.patch(
                'requests.get',
                mock.Mock(side_effect=lambda k, *args, **kwargs: resp)):
            new_f_obj = utils.Package.from_location(
                name='foo.bar.baz', base_url='http://127.0.0.1').file()
            self.assertTrue(hasattr(new_f_obj, 'read'))


class BundleTest(testtools.TestCase):
    base_url = "http://127.0.0.1"

    @requests_mock.mock()
    def test_packages(self, m):
        s = io.StringIO()
        bundle_contents = {'Packages': [
            {'Name': 'first_app'},
            {'Name': 'second_app', 'Version': '1.0'}
        ]}
        json.dump(bundle_contents, s)
        s.seek(0)
        bundle = utils.Bundle.from_file(s)
        self.assertEqual(
            set(['first_app', 'second_app']),
            set([p['Name'] for p in bundle.package_specs()])
        )

        # setup packages
        pkg1 = make_pkg({'FullName': 'first_app'})
        pkg2 = make_pkg({'FullName': 'second_app'})

        m.get(self.base_url + '/apps/first_app.zip', body=pkg1)
        m.get(self.base_url + '/apps/second_app.1.0.zip', body=pkg2)
        self.assertEqual(
            set(['first_app', 'second_app']),
            set([p.manifest['FullName']
                 for p in
                 bundle.packages(base_url=self.base_url)])
        )


class TraverseTest(testtools.TestCase):

    def test_traverse_and_replace(self):
        obj = [
            {'id': '===id1==='},
            {'id': '===id2===', 'x': [{'bar': '===id1==='}]},
            ['===id1===', '===id2==='],
            '===id3===',
            '===nonid0===',
            '===id3===',
        ]
        utils.traverse_and_replace(obj)
        self.assertNotEqual('===id1===', obj[0]['id'])
        self.assertNotEqual('===id2===', obj[1]['id'])
        self.assertNotEqual('===id1===', obj[1]['x'][0]['bar'])
        self.assertNotEqual('===id1===', obj[2][0])
        self.assertNotEqual('===id2===', obj[2][1])
        self.assertNotEqual('===id3===', obj[3])
        self.assertEqual('===nonid0===', obj[4])
        self.assertNotEqual('===id3===', obj[5])

        self.assertEqual(obj[0]['id'], obj[1]['x'][0]['bar'])
        self.assertEqual(obj[0]['id'], obj[2][0])

        self.assertEqual(obj[1]['id'], obj[2][1])

        self.assertEqual(obj[3], obj[5])
