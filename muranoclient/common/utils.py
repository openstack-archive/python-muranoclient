# Copyright 2012 OpenStack LLC.
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

from __future__ import print_function

import collections
import os
import re
import shutil
import StringIO
import sys
import tempfile
import textwrap
import urlparse
import uuid
import warnings
import zipfile

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import importutils
import prettytable
import requests
import six
import yaml
import yaql

from muranoclient.common import exceptions

try:
    import yaql.language  # noqa

    from muranoclient.common.yaqlexpression import YaqlExpression
except ImportError:
    # no yaql.language means legacy yaql
    from muranoclient.common.yaqlexpression_legacy import YaqlExpression


LOG = logging.getLogger(__name__)


# Decorator for cli-args
def arg(*args, **kwargs):
    def _decorator(func):
        # Because of the sematics of decorator composition if we just append
        # to the options list positional options will appear to be backwards.
        func.__dict__.setdefault('arguments', []).insert(0, (args, kwargs))
        return func
    return _decorator


def json_formatter(js):
    return jsonutils.dumps(js, indent=2)


def text_wrap_formatter(d):
    return '\n'.join(textwrap.wrap(d or '', 55))


def pretty_choice_list(l):
    return ', '.join("'%s'" % i for i in l)


def print_list(objs, fields, field_labels, formatters={}, sortby=0):
    pt = prettytable.PrettyTable([f for f in field_labels], caching=False)
    pt.align = 'l'

    for o in objs:
        row = []
        for field in fields:
            if field in formatters:
                row.append(formatters[field](o))
            else:
                data = getattr(o, field, None) or ''
                row.append(data)
        pt.add_row(row)
    print(encodeutils.safe_encode(pt.get_string()))


def print_dict(d, formatters={}):
    pt = prettytable.PrettyTable(['Property', 'Value'], caching=False)
    pt.align = 'l'

    for field in d.keys():
        if field in formatters:
            pt.add_row([field, formatters[field](d[field])])
        else:
            pt.add_row([field, d[field]])
    print(encodeutils.safe_encode(pt.get_string(sortby='Property')))


def find_resource(manager, name_or_id, *args, **kwargs):
    """Helper for the _find_* methods."""
    # first try to get entity as integer id
    try:
        if isinstance(name_or_id, int) or name_or_id.isdigit():
            return manager.get(int(name_or_id), *args, **kwargs)
    except exceptions.NotFound:
        pass

    # now try to get entity as uuid
    try:
        uuid.UUID(str(name_or_id))
        return manager.get(name_or_id, *args, **kwargs)
    except (ValueError, exceptions.NotFound):
        pass

    # finally try to find entity by name
    try:
        return manager.find(name=name_or_id)
    except exceptions.NotFound:
        msg = "No %s with a name or ID of '%s' exists." % \
              (manager.resource_class.__name__.lower(), name_or_id)
        raise exceptions.CommandError(msg)


def string_to_bool(arg):
    return arg.strip().lower() in ('t', 'true', 'yes', '1')


def env(*vars, **kwargs):
    """Search for the first defined of possibly many env vars

    Returns the first environment variable defined in vars, or
    returns the default defined in kwargs.
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


def import_versioned_module(version, submodule=None):
    module = 'muranoclient.v%s' % version
    if submodule:
        module = '.'.join((module, submodule))
    return importutils.import_module(module)


def exit(msg=''):
    if msg:
        print(encodeutils.safe_encode(msg), file=sys.stderr)
    sys.exit(1)


def getsockopt(self, *args, **kwargs):
    """A function which allows us to monkey patch eventlet's
    GreenSocket, adding a required 'getsockopt' method.
    TODO: (mclaren) we can remove this once the eventlet fix
    (https://bitbucket.org/eventlet/eventlet/commits/609f230)
    lands in mainstream packages.
    NOTE: Already in 0.13, but we can't be sure that all clients
    that use python-muranoclient also use newest eventlet
    """
    return self.fd.getsockopt(*args, **kwargs)


def exception_to_str(exc):
    try:
        error = six.text_type(exc)
    except UnicodeError:
        try:
            error = str(exc)
        except UnicodeError:
            error = ("Caught '%(exception)s' exception." %
                     {"exception": exc.__class__.__name__})
    return encodeutils.safe_encode(error, errors='ignore')


class NoCloseProxy(object):
    """A proxy object, that does nothing on close."""
    def __init__(self, obj):
        self.obj = obj

    def close(self):
        return

    def __getattr__(self, name):
        return getattr(self.obj, name)


class File(object):
    def __init__(self, name):
        self.name = name

    def open(self):
        if hasattr(self.name, 'read'):
            # NOTE(kzaitsev) We do not want to close a file object
            # passed to File wrapper. The caller should be responsible
            # for closing it
            return NoCloseProxy(self.name)
        else:
            if os.path.isfile(self.name):
                return open(self.name)
            url = urlparse.urlparse(self.name)
            if url.scheme in ('http', 'https'):
                resp = requests.get(self.name, stream=True)
                if not resp.ok:
                    raise ValueError("Got non-ok status({0}) "
                                     "while connecting to {1}".format(
                                         resp.status_code, self.name))
                temp_file = tempfile.NamedTemporaryFile()
                for chunk in resp.iter_content(1024 * 1024):
                    temp_file.write(chunk)
                temp_file.flush()
                temp_file.seek(0)
                return temp_file
            raise ValueError("Can't open {0}".format(self.name))


def to_url(filename, base_url, version='', path='/', extension=''):
    if urlparse.urlparse(filename).scheme in ('http', 'https'):
        return filename
    if not base_url:
        raise ValueError("No base_url for repository supplied")
    if '/' in filename or filename in ('.', '..'):
        raise ValueError("Invalid filename path supplied: {0}".format(
            filename))
    version = '.' + version if version else ''
    return urlparse.urljoin(base_url, path + filename + version + extension)


class FileWrapperMixin(object):
    def __init__(self, file_wrapper):
        self.file_wrapper = file_wrapper
        try:
            self._file = self.file_wrapper.open()
        except Exception:
            # NOTE(kzaitsev): We need to have _file available at __del__ time.
            self._file = None
            raise

    def file(self):
        self._file.seek(0)
        return self._file

    def close(self):
        if self._file and not self._file.closed:
            self._file.close()

    def save(self, dst):
        file_name = self.file_wrapper.name

        if urlparse.urlparse(file_name).scheme:
            file_name = file_name.split('/')[-1]

        dst = os.path.join(dst, file_name)

        with open(dst, 'wb') as dst_file:
            self._file.seek(0)
            shutil.copyfileobj(self._file, dst_file)

    def __del__(self):
        self.close()


class Package(FileWrapperMixin):
    """Represents murano package contents."""

    @staticmethod
    def from_file(file_obj):
        if not isinstance(file_obj, File):
            file_obj = File(file_obj)
        return Package(file_obj)

    @staticmethod
    def fromFile(file_obj):
        warnings.warn("Use from_file function", DeprecationWarning)
        return Package.from_file(file_obj)

    @staticmethod
    def from_location(name, base_url='', version='', url='', path=None):
        """If path is supplied search for name file in the path, otherwise
        if url is supplied - open that url and finally search murano
        repository for the package.
        """
        if path:
            pkg_name = os.path.join(path, name)
            file_name = None
            for f in [pkg_name, pkg_name + '.zip']:
                if os.path.exists(f):
                    file_name = f
            if file_name:
                return Package.from_file(file_name)
            LOG.error("Couldn't find file for package {0}, tried {1}".format(
                name, [pkg_name, pkg_name + '.zip']))
        if url:
            return Package.from_file(url)
        return Package.from_file(to_url(
            name,
            base_url=base_url,
            version=version,
            path='/apps/',
            extension='.zip')
        )

    @property
    def contents(self):
        """Contents of a package."""
        if not hasattr(self, '_contents'):
            try:
                self._file.seek(0)
                self._zip_obj = zipfile.ZipFile(
                    StringIO.StringIO(self._file.read()))
            except Exception as e:
                LOG.error("Error {0} occurred,"
                          " while parsing the package".format(e))
                raise
        return self._zip_obj

    @property
    def manifest(self):
        """Parsed manifest file of a package."""
        if not hasattr(self, '_manifest'):
            try:
                self._manifest = yaml.safe_load(
                    self.contents.open('manifest.yaml'))
            except Exception as e:
                LOG.error("Error {0} occurred, while extracting "
                          "manifest from package".format(e))
                raise
        return self._manifest

    def images(self):
        """Returns a list of required image specifications."""
        if 'images.lst' not in self.contents.namelist():
            return []
        try:
            return yaml.safe_load(
                self.contents.open('images.lst')).get('Images', [])
        except Exception:
            return []

    @property
    def classes(self):
        if not hasattr(self, '_classes'):
            self._classes = {}
            for class_name, class_file in six.iteritems(
                    self.manifest.get('Classes', {})):
                filename = "Classes/%s" % class_file
                if filename not in self.contents.namelist():
                    continue
                klass = yaml.safe_load(self.contents.open(filename))
                self._classes[class_name] = klass
        return self._classes

    @property
    def ui(self):
        if not hasattr(self, '_ui'):
            if 'UI/ui.yaml' in self.contents.namelist():
                self._ui = self.contents.open('UI/ui.yaml')
            else:
                self._ui = None
        return self._ui

    @property
    def logo(self):
        if not hasattr(self, '_logo'):
            if 'logo.png' in self.contents.namelist():
                self._logo = self.contents.open('logo.png')
            else:
                self._logo = None
        return self._logo

    def requirements(self, base_url, path=None, dep_dict=None):
        """Recursively scan Require section of manifests of all the
        dependencies. Returns a dict with FQPNs as keys and respective
        Package objects as values
        """
        if not dep_dict:
            dep_dict = {}
        dep_dict[self.manifest['FullName']] = self
        if 'Require' in self.manifest:
            for dep_name, ver in self.manifest['Require'].iteritems():
                if dep_name in dep_dict:
                    continue
                try:
                    req_file = Package.from_location(
                        dep_name,
                        version=ver,
                        path=path,
                        base_url=base_url,
                    )
                except Exception as e:
                    LOG.error("Error {0} occured while parsing package {1}, "
                              "required by {2} package".format(
                                  e, dep_name,
                                  self.manifest['FullName']))
                    continue
                dep_dict.update(req_file.requirements(
                    base_url=base_url,
                    path=path,
                    dep_dict=dep_dict,
                ))
        return dep_dict


def save_image_local(image_spec, base_url, dst):
    dst = os.path.join(dst, image_spec['Name'])

    download_url = to_url(
        image_spec.get("Url", image_spec['Name']),
        base_url=base_url,
        path='/images/'
    )

    with open(dst, "wb") as image_file:
        response = requests.get(download_url, stream=True)
        total_length = response.headers.get('content-length')

        if total_length is None:
            image_file.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for chunk in response.iter_content(1024 * 1024):
                dl += len(chunk)
                image_file.write(chunk)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[{0}{1}]".
                                 format('=' * done, ' ' * (50 - done)))
                sys.stdout.flush()
            sys.stdout.write("\n")
            image_file.flush()


def ensure_images(glance_client, image_specs, base_url, local_path=None):
    """Ensure that images from image_specs are available in glance. If not
    attempts: instructs glance to download the images and sets murano-specific
    metadata for it.
    """
    def _image_valid(image, keys):
        for key in keys:
            if key not in image:
                LOG.warning("Image specification invalid: "
                            "No {0} key in image ".format(key))
                return False
        return True

    keys = ['Name', 'DiskFormat', 'ContainerFormat', ]
    installed_images = []
    for image_spec in image_specs:
        if not _image_valid(image_spec, keys):
            continue
        filters = {
            'name': image_spec["Name"],
            'disk_format': image_spec["DiskFormat"],
            'container_format': image_spec["ContainerFormat"],
        }

        images = glance_client.images.list(filters=filters)
        try:
            img = images.next().to_dict()
        except StopIteration:
            img = None

        update_metadata = False
        if img:
            LOG.info("Found desired image {0}, id {1}".format(
                img['name'], img['id']))
            # check for murano meta-data
            if 'murano_image_info' in img.get('properties', {}):
                LOG.info("Image {0} already has murano meta-data".format(
                    image_spec['Name']))
            else:
                update_metadata = True
        else:
            LOG.info("Desired image {0} not found attempting "
                     "to download".format(image_spec['Name']))
            update_metadata = True

            img_file = None
            if local_path:
                img_file = os.path.join(local_path, image_spec['Name'])

            if img_file and not os.path.exists(img_file):
                LOG.error("Image file {0} does not exist."
                          .format(img_file))

            if img_file and os.path.exists(img_file):
                img = glance_client.images.create(
                    name=image_spec['Name'],
                    container_format=image_spec['ContainerFormat'],
                    disk_format=image_spec['DiskFormat'],
                    data=open(img_file, 'rb'),
                )
                img = img.to_dict()
            else:
                download_url = to_url(
                    image_spec.get("Url", image_spec['Name']),
                    base_url=base_url,
                    path='/images/',
                )
                LOG.info("Instructing glance to download image {0}".format(
                    image_spec['Name']))
                img = glance_client.images.create(
                    name=image_spec["Name"],
                    container_format=image_spec['ContainerFormat'],
                    disk_format=image_spec['DiskFormat'],
                    copy_from=download_url)
                img = img.to_dict()
            installed_images.append(img)

            if update_metadata and 'Meta' in image_spec:
                LOG.info("Updating image {0} metadata".format(
                    image_spec['Name']))
                murano_image_info = jsonutils.dumps(image_spec['Meta'])
                glance_client.images.update(
                    img['id'], properties={'murano_image_info':
                                           murano_image_info})
    return installed_images


class Bundle(FileWrapperMixin):
    """Represents murano bundle contents."""

    @staticmethod
    def from_file(file_obj):
        if not isinstance(file_obj, File):
            file_obj = File(file_obj)
        return Bundle(file_obj)

    @staticmethod
    def fromFile(file_obj):
        warnings.warn("Use from_file function", DeprecationWarning)
        return Bundle.from_file(file_obj)

    def package_specs(self):
        """Returns a generator yielding package specifications i.e.
        dicts with 'Name' and 'Version' fields
        """
        self._file.seek(0)
        bundle = None
        try:
            bundle = jsonutils.load(self._file)
        except ValueError:
            pass
        if bundle is None:
            try:
                bundle = yaml.safe_load(self._file)
            except yaml.error.YAMLError:
                pass

        if bundle is None:
            raise ValueError("Can't parse bundle contents")

        if 'Packages' not in bundle:
            return

        for package in bundle['Packages']:
            if 'Name' not in package:
                continue
            yield package

    def packages(self, base_url='', path=None):
        """Returns a generator, yielding Package objects for each package
        found in the bundle.
        """
        for package in self.package_specs():
            try:
                pkg_obj = Package.from_location(
                    package['Name'],
                    version=package.get('Version'),
                    url=package.get('Url'),
                    path=path,
                    base_url=base_url,
                )

            except Exception as e:
                LOG.error("Error {0} occured while obtaining "
                          "package {1}".format(e, package['Name']))
                continue
            yield pkg_obj


class YaqlYamlLoader(yaml.Loader):
    pass

# workaround for PyYAML bug: http://pyyaml.org/ticket/221
resolvers = {}
for k, v in yaml.Loader.yaml_implicit_resolvers.items():
    resolvers[k] = v[:]
YaqlYamlLoader.yaml_implicit_resolvers = resolvers


def yaql_constructor(loader, node):
    value = loader.construct_scalar(node)
    return YaqlExpression(value)

YaqlYamlLoader.add_constructor(u'!yaql', yaql_constructor)
YaqlYamlLoader.add_implicit_resolver(u'!yaql', YaqlExpression, None)


def traverse_and_replace(obj,
                         pattern=re.compile(r'^===id(\d+)===$'),
                         replacements=None):
    """Helper function that traverses object model and substitutes ids.

    Recursively checks values of objects found in `obj` against `pattern`,
    and replaces strings that match pattern with uuid.uuid4(). Keeps track of
    any replacements already made, i.e. ===id1=== would always be the same,
    across `obj`. Uses 1st group, found in the `pattern` regexp as unique
    identifier of a replacement
    """
    if replacements is None:
        replacements = collections.defaultdict(lambda: uuid.uuid4().hex)

    def _maybe_replace(obj, key, value):
        """Check and replace value against pattern"""
        if isinstance(value, six.string_types):
            m = pattern.search(value)
            if m:
                if m.group(1) not in replacements:
                    replacements[m.group(1)] = uuid.uuid4().hex
                obj[key] = replacements[m.group(1)]

    if isinstance(obj, list):
        for key, value in enumerate(obj):
            if isinstance(value, (list, dict)):
                traverse_and_replace(value, pattern, replacements)
            else:
                _maybe_replace(obj, key, value)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (list, dict)):
                traverse_and_replace(value, pattern, replacements)
            else:
                _maybe_replace(obj, key, value)
    else:
        _maybe_replace(obj, key, value)
