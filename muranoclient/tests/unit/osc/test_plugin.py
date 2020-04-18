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

from unittest import mock

from muranoclient.osc import plugin
from muranoclient.tests.unit import base


class TestApplicationCatalogPlugin(base.TestCaseShell):

    @mock.patch("muranoclient.v1.client.Client")
    def test_make_client(self, p_client):

        instance = mock.Mock()
        instance._api_version = {"application_catalog": '1'}
        instance._region_name = 'murano_region'
        instance.session = 'murano_session'

        plugin.make_client(instance)
        p_client.assert_called_with(
            mock.ANY,
            region_name='murano_region',
            session='murano_session',
            service_type='application-catalog')
