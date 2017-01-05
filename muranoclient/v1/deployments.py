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

from muranoclient.common import base


class Deployment(base.Resource):
    def __repr__(self):
        return '<Deployment %s>' % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class Status(base.Resource):
    def __repr__(self):
        return '<Status %s>' % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class DeploymentManager(base.Manager):
    resource_class = Deployment

    def list(self, environment_id, all_environments=False):
        if all_environments:
            return self._list('/v1/deployments', 'deployments')
        else:
            return self._list('/v1/environments/{id}/deployments'.
                              format(id=environment_id), 'deployments')

    def reports(self, environment_id, deployment_id, *service_ids):
        path = '/v1/environments/{id}/deployments/{deployment_id}'
        path = path.format(id=environment_id, deployment_id=deployment_id)
        if service_ids:
            for service_id in service_ids:
                path += '?service_id={0}'.format(service_id)

        resp, body = self.api.json_request(path, 'GET')

        data = body.get('reports', [])
        return [Status(self, res, loaded=True) for res in data if res]
