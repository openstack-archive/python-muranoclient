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
from functools import wraps

from muranoclient.common import base


def normalize_path(f):
    @wraps(f)
    def f_normalize_path(*args, **kwargs):
        if kwargs['path'][0] == '/':
            kwargs['path'] = kwargs['path'][1:]
        return f(*args, **kwargs)

    return f_normalize_path


class Service(base.Resource):
    def __repr__(self):
        return '<Service %s>' % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class ServiceManager(base.Manager):
    resource_class = Service

    @normalize_path
    def get(self, environment_id, path, session_id=None):
        if session_id:
            headers = {'X-Configuration-Session': session_id}
        else:
            headers = {}

        return self._list('environments/{0}/services/{1}'.
                          format(environment_id, path), headers=headers)

    @normalize_path
    def post(self, environment_id, path, data, session_id):
        headers = {'X-Configuration-Session': session_id}

        return self._create('environments/{id}/services/{1}'.
                            format(environment_id, path), data,
                            headers=headers)

    @normalize_path
    def put(self, environment_id, path, data, session_id):
        headers = {'X-Configuration-Session': session_id}

        return self._update('environments/{id}/services/{1}'.
                            format(environment_id, path), data,
                            headers=headers)

    @normalize_path
    def delete(self, environment_id, path, session_id):
        headers = {'X-Configuration-Session': session_id}
        path = 'environments/{0}/services/{1}'.format(environment_id, path)

        return self._delete(path, headers=headers)
