#    Copyright (c) 2014 Mirantis, Inc.
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

import json
from muranoclient.common import base
from muranoclient.common import exceptions
import requests
import yaml


class Package(base.Resource):
    def __repr__(self):
        return "<Package %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class Category(base.Resource):
    def __init__(self, manager, info, loaded=False):
        self.value = info

    def __unicode__(self):
        return self.value

    def __repr__(self):
        return self.value


class PackageManager(base.Manager):
    resource_class = Package

    def list(self):
        return self._list('/v1/catalog/packages', 'packages')

    def categories(self):
        return self._list('/v1/catalog/packages/categories',
                          response_key='categories', obj_class=Category)

    def create(self, data, files):
        data = {'data': json.dumps(data)}
        url = '{0}/v1/catalog/packages'.format(self.api.endpoint)
        headers = {'X-Auth-Token': self.api.auth_token}
        response = requests.post(url, data=data, files=files, headers=headers)
        if not response.ok:
            setattr(response, 'status', response.status_code)
            raise exceptions.from_response(response)
        return response

    def get(self, app_id):
        return self._get('/v1/catalog/packages/{0}'.format(app_id))

    def delete(self, app_id):
        return self._delete('/v1/catalog/packages/{0}'.format(app_id))

    def download(self, app_id):
        url = '/v1/catalog/packages/{0}/download'.format(app_id)
        response, iterator = self.api.raw_request('GET', url)
        if response.status == 200:
            return ''.join(iterator)
        else:
            raise exceptions.from_response(response)

    def get_ui(self, app_id):
        url = '/v1/catalog/packages/{0}/ui'.format(app_id)
        response, iterator = self.api.raw_request('GET', url)
        if response.status == 200:
            return yaml.load(''.join(iterator))
        else:
            raise exceptions.from_response(response)

    def get_logo(self, app_id):
        url = '/v1/catalog/packages/{0}/logo'.format(app_id)
        response, iterator = self.api.raw_request('GET', url)
        if response.status == 200:
            return ''.join(iterator)
        else:
            raise exceptions.from_response(response)
