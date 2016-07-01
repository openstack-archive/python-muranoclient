# Copyright (c) 2016 Mirantis, Inc.
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


class StaticActionResult(object):
    def __init__(self, result, exception=None):
        self._result = result
        self._exception = exception

    def get_result(self):
        if self._exception:
            raise self._exception
        return self._result

    def check_result(self):
        return True


# Not a true manager yet; should be changed to be one if CRUD
# functionality becomes available for actions.
class StaticActionManager(object):
    def __init__(self, api):
        self.api = api

    def call(self, arguments):
        url = '/v1/actions'
        try:
            resp, body = self.api.json_request(url, 'POST', data=arguments)
            return StaticActionResult(body)
        except Exception as e:
            if e.code >= 500:
                raise
            return StaticActionResult(None, exception=e)
