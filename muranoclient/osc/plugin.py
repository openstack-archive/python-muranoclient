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

from osc_lib import utils
from oslo_log import log as logging

from muranoclient.i18n import _

LOG = logging.getLogger(__name__)

DEFAULT_APPLICATION_CATALOG_API_VERSION = "1"
API_VERSION_OPTION = "os_application_catalog_api_version"
API_NAME = "application_catalog"
API_VERSIONS = {
    '1': 'muranoclient.v1.client.Client',
}


def make_client(instance):
    """Returns an application-catalog service client"""
    application_catalog_client = utils.get_client_class(
        API_NAME,
        instance._api_version[API_NAME],
        API_VERSIONS)
    LOG.debug("Instantiating application-catalog client: {0}".format(
              application_catalog_client))

    client = application_catalog_client(
        instance.get_configuration().get('murano_url'),
        region_name=instance._region_name,
        session=instance.session,
        service_type='application-catalog',
    )
    return client


def build_option_parser(parser):
    """Hook to add global options"""
    parser.add_argument(
        '--os-application-catalog-api-version',
        metavar='<application-catalog-api-version>',
        default=utils.env(
            'OS_APPLICATION_CATALOG_API_VERSION',
            default=DEFAULT_APPLICATION_CATALOG_API_VERSION),
        help=_("Application catalog API version, default={0}"
               "(Env:OS_APPLICATION_CATALOG_API_VERSION)").format(
                   DEFAULT_APPLICATION_CATALOG_API_VERSION))
    parser.add_argument('--murano-url',
                        default=utils.env('MURANO_URL'),
                        help=_('Defaults to env[MURANO_URL].'))
    return parser
