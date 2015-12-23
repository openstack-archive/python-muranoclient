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

"""
Base utilities to build API operation managers and objects on top of.
"""

import abc
import copy

import six

from muranoclient.openstack.common.apiclient import exceptions


# Python 2.4 compat
try:
    all
except NameError:
    def all(iterable):
        return True not in (not x for x in iterable)


def getid(obj):
    """Abstracts the common pattern of allowing both an object or
    an object's ID (UUID) as a parameter when dealing with relationships.
    """
    try:
        return obj.id
    except AttributeError:
        return obj


class Manager(object):
    """Managers interact with a particular type of API (servers, flavors,
    images, etc.) and provide CRUD operations for them.
    """
    resource_class = None

    def __init__(self, api):
        self.api = api

    def _list(self, url, response_key=None, obj_class=None,
              data=None, headers=None):

        if headers is None:
            headers = {}
        resp, body = self.api.json_request('GET', url, headers=headers)

        if obj_class is None:
            obj_class = self.resource_class

        if response_key:
            if response_key not in body:
                body[response_key] = []
            data = body[response_key]
        else:
            data = body
        return [obj_class(self, res, loaded=True) for res in data if res]

    def _delete(self, url, headers=None):
        if headers is None:
            headers = {}
        self.api.raw_request('DELETE', url, headers=headers)

    def _update(self, url, data, response_key=None, headers=None):
        if headers is None:
            headers = {}
        resp, body = self.api.json_request('PUT', url, data=data,
                                           headers=headers)
        # PUT requests may not return a body
        if body:
            if response_key:
                return self.resource_class(self, body[response_key])
            return self.resource_class(self, body)

    def _create(self, url, data=None, response_key=None,
                return_raw=False, headers=None):
        if headers is None:
            headers = {}
        if data:
            resp, body = self.api.json_request('POST', url,
                                               data=data, headers=headers)
        else:
            resp, body = self.api.json_request('POST', url, headers=headers)
        if return_raw:
            if response_key:
                return body[response_key]
            return body
        if response_key:
            return self.resource_class(self, body[response_key])
        return self.resource_class(self, body)

    def _get(self, url, response_key=None, return_raw=False, headers=None):
        if headers is None:
            headers = {}
        resp, body = self.api.json_request('GET', url, headers=headers)
        if return_raw:
            if response_key:
                return body[response_key]
            return body
        if response_key:
            return self.resource_class(self, body[response_key])
        return self.resource_class(self, body)


@six.add_metaclass(abc.ABCMeta)
class ManagerWithFind(Manager):
    """Manager with additional `find()`/`findall()` methods."""

    @abc.abstractmethod
    def list(self):
        pass

    def find(self, **kwargs):
        """Find a single item with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
        """
        rl = self.findall(**kwargs)
        num = len(rl)

        if num == 0:
            msg = "No %s matching %s." % (self.resource_class.__name__, kwargs)
            raise exceptions.NotFound(msg)
        elif num > 1:
            raise exceptions.NoUniqueMatch
        else:
            return self.get(rl[0].id)

    def findall(self, **kwargs):
        """Find all items with attributes matching ``**kwargs``.

        This isn't very efficient: it loads the entire list then filters on
        the Python side.
        """
        found = []
        searches = kwargs.items()

        for obj in self.list():
            try:
                if all(getattr(obj, attr) == value
                       for (attr, value) in searches):
                    found.append(obj)
            except AttributeError:
                continue

        return found


class Resource(object):
    """A resource represents a particular instance of an object (tenant, user,
    etc). This is pretty much just a bag for attributes.

    :param manager: Manager object
    :param info: dictionary representing resource attributes
    :param loaded: prevent lazy-loading if set to True
    """
    def __init__(self, manager, info, loaded=False):
        self.manager = manager
        self._info = info
        self._add_details(info)
        self._loaded = loaded

    def _add_details(self, info):
        for k, v in info.items():
            setattr(self, k, v)

    def __setstate__(self, d):
        for k, v in d.items():
            setattr(self, k, v)

    def __getattr__(self, k):
        if k not in self.__dict__:
            # NOTE(bcwaldon): disallow lazy-loading if already loaded once
            if not self.is_loaded():
                self.get()
                return self.__getattr__(k)
            raise AttributeError(k)
        else:
            return self.__dict__[k]

    def __repr__(self):
        reprkeys = sorted(k for k in self.__dict__.keys() if k[0] != '_' and
                          k != 'manager')
        info = ", ".join("%s=%s" % (k, getattr(self, k)) for k in reprkeys)
        return "<%s %s>" % (self.__class__.__name__, info)

    def get(self):
        # set_loaded() first ... so if we have to bail, we know we tried.
        self.set_loaded(True)
        if not hasattr(self.manager, 'get'):
            return

        new = self.manager.get(self.id)
        if new:
            self._add_details(new._info)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self._info == other._info

    def is_loaded(self):
        return self._loaded

    def set_loaded(self, val):
        self._loaded = val

    def to_dict(self):
        return copy.deepcopy(self._info)
