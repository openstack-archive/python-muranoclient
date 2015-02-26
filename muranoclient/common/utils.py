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

import os
import re
import sys
import tempfile
import textwrap
import types
import urlparse
import uuid

from oslo.serialization import jsonutils
from oslo.utils import encodeutils
from oslo.utils import importutils
import prettytable
import requests
import six
import yaml
import yaql
import yaql.exceptions

from muranoclient.common import exceptions


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


def find_resource(manager, name_or_id):
    """Helper for the _find_* methods."""
    # first try to get entity as integer id
    try:
        if isinstance(name_or_id, int) or name_or_id.isdigit():
            return manager.get(int(name_or_id))
    except exceptions.NotFound:
        pass

    # now try to get entity as uuid
    try:
        uuid.UUID(str(name_or_id))
        return manager.get(name_or_id)
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


class Package(object):
    """Represents murano package contents."""

    @staticmethod
    def fromFile(file_obj):
        if not isinstance(file_obj, File):
            file_obj = File(file_obj)
        return Package(file_obj)

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

    def __del__(self):
        self.close()


class YaqlExpression(object):
    def __init__(self, expression):
        self._expression = str(expression)
        self._parsed_expression = yaql.parse(self._expression)

    def expression(self):
        return self._expression

    def __repr__(self):
        return 'YAQL(%s)' % self._expression

    def __str__(self):
        return self._expression

    @staticmethod
    def match(expr):
        if not isinstance(expr, types.StringTypes):
            return False
        if re.match('^[\s\w\d.:]*$', expr):
            return False
        try:
            yaql.parse(expr)
            return True
        except yaql.exceptions.YaqlGrammarException:
            return False
        except yaql.exceptions.YaqlLexicalException:
            return False

    def evaluate(self, data=None, context=None):
        return self._parsed_expression.evaluate(data=data, context=context)


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

yaml.add_constructor(u'!yaql', yaql_constructor, YaqlYamlLoader)
yaml.add_implicit_resolver(u'!yaql', YaqlExpression, Loader=YaqlYamlLoader)
