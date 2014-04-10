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


class InstanceStatistics(base.Resource):
    def __repr__(self):
        return "<Instance statistics %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class InstanceStatisticsManager(base.Manager):
    resource_class = InstanceStatistics

    def get(self, environment_id, instance_id=None):
        if instance_id:
            path = '/v1/environments/{id}/instance-statistics/raw/' \
                   '{instance_id}'.format(id=environment_id,
                                          instance_id=instance_id)
        else:
            path = '/v1/environments/{id}/instance-statistics/raw'.format(
                id=environment_id)
        return self._list(path, None)

    def get_aggregated(self, environment_id):
        path = '/v1/environments/{id}/instance-statistics/aggregated'.format(
            id=environment_id)
        return self._list(path, None)
