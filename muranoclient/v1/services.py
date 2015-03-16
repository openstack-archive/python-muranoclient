#    Copyright (c) 2013 Mirantis, Inc.
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

import functools
import posixpath
import types

from muranoclient.common import base


def normalize_path(f):
    @functools.wraps(f)
    def f_normalize_path(*args, **kwargs):
        path = args[2] if len(args) >= 3 else kwargs['path']

        # path formally is just absolute unix path
        if not posixpath.isabs(path):
            raise ValueError("Parameter 'path' should start with '/'")

        args = list(args)
        if len(args) >= 3:
            args[2] = args[2][1:]
        else:
            kwargs['path'] = kwargs['path'][1:]

        return f(*args, **kwargs)

    return f_normalize_path


class Service(base.Resource):
    def __repr__(self):
        return '<Service %s>' % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)

    def _add_details(self, info):
        if isinstance(info, dict):
            for k, v in info.items():
                setattr(self, k, v)


class ServiceManager(base.Manager):
    resource_class = Service

    def list(self, environment_id, session_id=None):
        if session_id:
            headers = {'X-Configuration-Session': session_id}
        else:
            headers = {}
        return self._list("/v1/environments/{0}/services".
                          format(environment_id), headers=headers)

    @normalize_path
    def get(self, environment_id, path, session_id=None):
        if session_id:
            headers = {'X-Configuration-Session': session_id}
        else:
            headers = {}

        return self._get('/v1/environments/{0}/services/{1}'.
                         format(environment_id, path), headers=headers)

    @normalize_path
    def post(self, environment_id, path, data, session_id):
        headers = {'X-Configuration-Session': session_id}

        result = self._create('/v1/environments/{0}/services/{1}'.
                              format(environment_id, path), data,
                              headers=headers, return_raw=True)

        if isinstance(result, types.ListType):
            return [self.resource_class(self, item) for item in result]
        else:
            return self.resource_class(self, result)

    @normalize_path
    def put(self, environment_id, path, data, session_id):
        headers = {'X-Configuration-Session': session_id}

        return self._update('/v1/environments/{0}/services/{1}'.
                            format(environment_id, path), data,
                            headers=headers)

    @normalize_path
    def delete(self, environment_id, path, session_id):
        headers = {'X-Configuration-Session': session_id}
        path = '/v1/environments/{0}/services/{1}'.format(environment_id, path)

        return self._delete(path, headers=headers)
