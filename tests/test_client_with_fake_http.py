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

import unittest2 as unittest
import logging
from httpretty import HTTPretty, httprettified
from muranoclient.client import Client


LOG = logging.getLogger('Unit tests')


@unittest.skip
class UnitTestsForClassesAndFunctions(unittest.TestCase):
    @httprettified
    def test_client_env_list_with_empty_list(self):
        HTTPretty.register_uri(HTTPretty.GET,
                               "http://no-resolved-host:8001/environments",
                               body='{"environments": []}',
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.environments.list()
        assert result == []

    @httprettified
    def test_client_env_list_with_elements(self):
        body = ('{"environments":['
                '{"id": "0ce373a477f211e187a55404a662f968",'
                '"name": "dc1",'
                '"created": "2010-11-30T03:23:42Z",'
                '"updated": "2010-11-30T03:23:44Z",'
                '"tenant-id": "0849006f7ce94961b3aab4e46d6f229a"},'
                '{"id": "0ce373a477f211e187a55404a662f961",'
                '"name": "dc2",'
                '"created": "2010-11-30T03:23:42Z",'
                '"updated": "2010-11-30T03:23:44Z",'
                '"tenant-id": "0849006f7ce94961b3aab4e4626f229a"}'
                ']}')
        HTTPretty.register_uri(HTTPretty.GET,
                               "http://no-resolved-host:8001/environments",
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.environments.list()
        assert result[0].name == 'dc1'
        assert result[-1].name == 'dc2'

    @httprettified
    def test_client_env_create(self):
        body = ('{"id": "0ce373a477f211e187a55404a662f968",'
                '"name": "test",'
                '"created": "2010-11-30T03:23:42Z",'
                '"updated": "2010-11-30T03:23:44Z",'
                '"tenant-id": "0849006f7ce94961b3aab4e46d6f229a"}')
        HTTPretty.register_uri(HTTPretty.POST,
                               "http://no-resolved-host:8001/environments",
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.environments.create('test')
        assert result.name == 'test'

    @httprettified
    def test_client_ad_list(self):
        body = ('{"activeDirectories": [{'
                '"id": "1",'
                '"name": "dc1",'
                '"created": "2010-11-30T03:23:42Z",'
                '"updated": "2010-11-30T03:23:44Z",'
                '"configuration": "standalone",'
                '"units": [{'
                '"id": "0ce373a477f211e187a55404a662f961",'
                '"type": "master",'
                '"location": "test"}]}]}')
        url = ("http://no-resolved-host:8001/environments"
               "/1/activeDirectories")
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.activeDirectories.list('1', 'test')
        assert result[0].name == 'dc1'

    @httprettified
    def test_client_ad_create(self):
        body = ('{'
                '"id": "1",'
                '"name": "ad1",'
                '"created": "2010-11-30T03:23:42Z",'
                '"updated": "2010-11-30T03:23:44Z",'
                '"configuration": "standalone",'
                '"units": [{'
                '"id": "0ce373a477f211e187a55404a662f961",'
                '"type": "master",'
                '"location": "test"}]}')
        url = ("http://no-resolved-host:8001/environments"
               "/1/activeDirectories")
        HTTPretty.register_uri(HTTPretty.POST, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.services.post('1', 'test', 'ad1')
        assert result.name == 'ad1'

    @httprettified
    def test_client_ad_list_without_elements(self):
        body = '{"activeDirectories": []}'
        url = ("http://no-resolved-host:8001/environments"
               "/1/activeDirectories")
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.activeDirectories.list('1', 'test')
        assert result == []

    @httprettified
    def test_client_iis_list(self):
        body = ('{"webServers": [{'
                '"id": "1",'
                '"name": "iis11",'
                '"created": "2010-11-30T03:23:42Z",'
                '"updated": "2010-11-30T03:23:44Z",'
                '"domain": "acme",'
                '"units": [{'
                '"id": "0ce373a477f211e187a55404a662f961",'
                '"endpoint": {"host": "1.1.1.1"},'
                '"location": "test"}]}]}')
        url = ("http://no-resolved-host:8001/environments"
               "/1/webServers")
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.webServers.list('1', 'test')
        assert result[0].name == 'iis11'

    @httprettified
    def test_client_iis_create(self):
        body = ('{'
                '"id": "1",'
                '"name": "iis12",'
                '"created": "2010-11-30T03:23:42Z",'
                '"updated": "2010-11-30T03:23:44Z",'
                '"domain": "acme",'
                '"units": [{'
                '"id": "0ce373a477f211e187a55404a662f961",'
                '"endpoint": {"host": "1.1.1.1"},'
                '"location": "test"}]}')
        url = ("http://no-resolved-host:8001/environments"
               "/1/webServers")
        HTTPretty.register_uri(HTTPretty.POST, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.webServers.create('1', 'test', 'iis12')
        assert result.name == 'iis12'

    @httprettified
    def test_client_iis_list_without_elements(self):
        body = '{"webServers": []}'
        url = ("http://no-resolved-host:8001/environments"
               "/1/webServers")
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.webServers.list('1', 'test')
        assert result == []

    @httprettified
    def test_client_aspapp_list(self):
        body = '''
{
    "aspNetApps":
    [
        {
            "id": "88f6ed99ff3645bcb84e1e37ab9ece3d",
            "name": "frontend",
            "created": "2010-11-30T03:23:42Z",
            "updated": "2010-11-30T03:23:44Z",
            "domain": "ACME",
            "repository": "https://github.com/Mirantis/murano-mvc-demo.git",
            "uri": "http://10.0.0.2",
            "units": [{
                "id": "59255829f0574297acc1cd3a18ff6fd7",
                "address": "10.0.0.2",
                "location": "west-dc"
            }]
        }, {
            "id": "aa49dcaff9914b8abb26855f0799b0e0",
            "name": "backend",
            "created": "2010-11-30T03:23:42Z",
            "updated": "2010-11-30T03:23:44Z",
            "repository": "https://github.com/Mirantis/murano-mvc-demo.git",
            "uri": "http://10.0.0.3",
            "domain": "ACME2" ,
            "units": [{
                "id": "274b54f6bbe6493690e7107aa947e112",
                "address": "10.0.0.3",
                "location": "west-dc"
            }]
        }
    ]
}
'''
        url = 'http://no-resolved-host:8001/environments' \
              '/1/aspNetApps'
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.aspNetApps.list('1', 'test')
        assert result[0].name == 'frontend'

    @httprettified
    def test_client_aspapp_create(self):
        body = '''
{
    "id": "88f6ed99ff3645bcb84e1e37ab9ece3d",
    "name": "frontend",
    "created": "2010-11-30T03:23:42Z",
    "updated": "2010-11-30T03:23:44Z",
    "domain": "ACME",
    "repository": "https://github.com/Mirantis/murano-mvc-demo.git",
    "uri": "http://10.0.0.2",
    "units": [{
        "id": "59255829f0574297acc1cd3a18ff6fd7",
        "address": "10.0.0.2",
        "location": "west-dc"
    }]
}
'''
        url = 'http://no-resolved-host:8001/environments' \
              '/1/aspNetApps'
        HTTPretty.register_uri(HTTPretty.POST, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.aspNetApps.create('1', 'test', 'test')
        assert result.name == 'frontend'

    @httprettified
    def test_client_aspapp_list_without_elements(self):
        body = '{"aspNetApps": []}'
        url = 'http://no-resolved-host:8001/environments' \
              '/1/aspNetApps'
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.aspNetApps.list('1', 'test')
        assert result == []

    @httprettified
    def test_client_webfarm_list(self):
        body = '''
{
    "webServerFarms":
    [
        {
            "id": "01fa4412ab4849acb27394aaf307ca88",
            "name": "frontend",
            "created": "2010-11-30T03:23:42Z",
            "updated": "2010-11-30T03:23:44Z",
            "domain": "ACME",
            "loadBalancerPort": 80,
            "uri": "http://192.168.1.1:80",
            "units":
            [
                {
                    "id": "a34992c8634b482798187d3c0e1c999a",
                    "address": "10.0.0.2",
                    "location": "west-dc"
                },
                {
                    "id": "fcd60488bb6f4acf97ccdb8f8fc6bc9a",
                    "address": "10.0.0.3",
                    "location": "west-dc"
                }
            ]
        }
    ]
}
'''
        url = 'http://no-resolved-host:8001/environments' \
              '/1/webServerFarms'
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.webServerFarms.list('1', 'test')
        assert result[0].name == 'frontend'

    @httprettified
    def test_client_webfarm_create(self):
        body = '''
{
    "name": "frontend",
    "domain": "ACME",
    "loadBalancerPort": 80,
    "uri": "http://192.168.1.1:80",
    "units":
    [
        {"location": "west-dc"},
        {"location": "west-dc"}
    ]
}
'''
        url = 'http://no-resolved-host:8001/environments' \
              '/1/webServerFarms'
        HTTPretty.register_uri(HTTPretty.POST, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.webServerFarms.create('1', 'test', 'test')
        assert result.name == 'frontend'

    @httprettified
    def test_client_webfarm_list_without_elements(self):
        body = '{"webServerFarms": []}'
        url = 'http://no-resolved-host:8001/environments' \
              '/1/webServerFarms'
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.webServerFarms.list('1', 'test')
        assert result == []

    @httprettified
    def test_client_aspappfarm_list(self):
        body = '''
{
    "aspNetAppFarms":
    [
        {
            "id": "01fa4412ab4849acb27394aaf307ca88",
            "name": "frontend",
            "created": "2010-11-30T03:23:42Z",
            "updated": "2010-11-30T03:23:44Z",
            "domain": "ACME",
            "loadBalancerPort": 80,
            "uri": "http://192.168.1.1:80",
            "units":
            [
                {
                    "id": "3374f4eb850e4b27bf734649d7004cc0",
                    "address": "10.0.0.2",
                    "location": "west-dc"
                },
                {
                    "id": "fcd60488bb6f4acf97ccdb8f8fc6bc9a",
                    "address": "10.0.0.3",
                    "location": "west-dc"
                }
            ]
        }
    ]
}
'''
        url = 'http://no-resolved-host:8001/environments' \
              '/1/aspNetAppFarms'
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.aspNetAppFarms.list('1', 'test')
        assert result[0].name == 'frontend'

    @httprettified
    def test_client_aspappfarm_create(self):
        body = '''
{
    "name": "frontend",
    "adminPassword": "password",
    "domain": "acme.dc",
    "loadBalancerPort": 80,
    "repository": "https://github.com/Mirantis/murano-mvc-demo.git",
    "units": [{
        "location": "west-dc"
    }]
}
'''
        url = 'http://no-resolved-host:8001/environments' \
              '/1/aspNetAppFarms'
        HTTPretty.register_uri(HTTPretty.POST, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.aspNetAppFarms.create('1', 'test', 'test')
        assert result.name == 'frontend'

    @httprettified
    def test_client_aspappfarm_list_without_elements(self):
        body = '{"aspNetAppFarms": []}'
        url = 'http://no-resolved-host:8001/environments' \
              '/1/aspNetAppFarms'
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=body,
                               adding_headers={
                                   'Content-Type': 'application/json', })
        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        result = test_client.aspNetAppFarms.list('1', 'test')
        assert result == []
