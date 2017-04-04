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
from six.moves import urllib

from muranoclient.common import base


class Environment(base.Resource):
    def __repr__(self):
        return "<Environment %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class Status(base.Resource):
    def __repr__(self):
        return '<Status %s>' % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class EnvironmentManager(base.ManagerWithFind):
    resource_class = Environment

    def list(self, all_tenants=False, tenant_id=None):
        params = {'all_tenants': all_tenants}
        if tenant_id:
            params['tenant'] = tenant_id
        path = '/v1/environments?{query}'.format(
            query=urllib.parse.urlencode(params))
        return self._list(path, 'environments')

    def create(self, data):
        return self._create('/v1/environments', data)

    def update(self, environment_id, name):
        return self._update('/v1/environments/{id}'.format(id=environment_id),
                            data={'name': name})

    def delete(self, environment_id, abandon=False):
        path = '/v1/environments/{id}?{query}'.format(
            id=environment_id,
            query=urllib.parse.urlencode({'abandon': abandon}))
        return self._delete(path)

    def get(self, environment_id, session_id=None):
        if session_id:
            headers = {'X-Configuration-Session': session_id}
        else:
            headers = {}
        return self._get("/v1/environments/{id}".format(id=environment_id),
                         headers=headers)

    def last_status(self, environment_id, session_id):
        headers = {'X-Configuration-Session': session_id}
        path = '/v1/environments/{id}/lastStatus'
        path = path.format(id=environment_id)
        status_dict = self._get(path, return_raw=True,
                                response_key='lastStatuses',
                                headers=headers)
        result = {}
        for k, v in status_dict.items():
            if v:
                result[k] = Status(self, v, loaded=True)
        return result

    def get_model(self, environment_id, path, session_id=None):
        headers = {'X-Configuration-Session': session_id}
        url = '/v1/environments/{id}/model/{path}'
        url = url.format(id=environment_id, path=path)
        return self._get(url, return_raw=True, headers=headers)

    def update_model(self, environment_id, data, session_id):
        headers = {'X-Configuration-Session': session_id}
        url = '/v1/environments/{id}/model/'
        url = url.format(id=environment_id)
        return self._update(url, data, return_raw=True, headers=headers,
                            method='PATCH',
                            content_type='application/env-model-json-patch')
