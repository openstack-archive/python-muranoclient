# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
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


# Not a true manager yet; should be changed to be one if CRUD
# functionality becomes available for actions.
class ActionManager(object):
    def __init__(self, api):
        self.api = api

    def call(self, environment_id, action_id, arguments=None):
        if arguments is None:
            arguments = {}
        url = '/v1/environments/{environment_id}/actions/{action_id}'.format(
            environment_id=environment_id, action_id=action_id)
        resp, body = self.api.json_request(url, 'POST', body=arguments)
        return body['task_id']

    def get_result(self, environment_id, task_id):
        url = '/v1/environments/{environment_id}/actions/{task_id}'.format(
            environment_id=environment_id, task_id=task_id)
        resp, body = self.api.json_request(url, 'GET')
        return body or None
