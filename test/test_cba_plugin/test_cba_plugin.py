##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from cbaplugin.cba_plugin import CbaPlugin
from cbaplugin.cba_exceptions import UnknownCbaCompException

from litp.extensions.core_extension import CoreExtension
from litp.core.execution_manager import ExecutionManager
from litp.core.execution_manager import CallbackExecutionException
from litp.core.model_manager import ModelManager
from litp.core.plugin_manager import PluginManager
from litp.core.puppet_manager import PuppetManager
from litp.core.model_type import ItemType, Child

import unittest
import sys


class MockHelperClass(object):
    def create_configuration(self, plugin_api_context, cluster):
        return []

    @staticmethod
    def do_callback(callback_api, method_name, *args, **kwargs):
        pass


class MockCallbackApiObject(object):
    pass


class MockPluginApi(object):
    def query(self, item_type):
        if item_type == 'cmw-cluster':
            return [MockCluster()]
        elif item_type == 'jboss-runtime':
            return [object]
        return []


class MockCluster(MockPluginApi):
    pass


class TestCbaPlugin(unittest.TestCase):

    def setUp(self):
        self.model = ModelManager()
        self.puppet_manager = PuppetManager(self.model)
        self.plugin_manager = PluginManager(self.model)
        self.execution = ExecutionManager(self.model,
                                          self.puppet_manager,
                                          self.plugin_manager)
        self.plugin_manager.add_property_types(
            CoreExtension().define_property_types())
        self.plugin_manager.add_item_types(
            CoreExtension().define_item_types())
        self.plugin_manager.add_default_model()

        self.plugin = CbaPlugin()
        self.plugin_manager.add_plugin('TestPlugin', 'some.test.plugin',
                                       '1.0.0', self.plugin)

        self.model.item_types.pop('root')
        self.model.register_item_type(ItemType("root",
            node1=Child("node"),
            node2=Child("node"),
        ))
        self.model.create_root_item("root", "/")

    def setup_model(self):
        self.node1 = self.model.create_item("node", "/node1",
                                                 hostname="node1")
        self.node2 = self.model.create_item("node", "/node2",
                                                 hostname="special")

    def test_validate_model(self):
        self.setup_model()
        errors = self.plugin.validate_model(self)
        self.assertEqual(len(errors), 0)

    def test_create_configuration(self):
        def _get_mock_helper_class(comp):
            return MockHelperClass()
        plugin = CbaPlugin()
        plugin_api = MockPluginApi()
        plugin._get_helper_class = _get_mock_helper_class
        self.setup_model()
        tasks = plugin.create_configuration(plugin_api)
        self.assertEqual(len(tasks), 0)

    def test_cba_callback_method(self):
        def _get_mock_helper_class(comp):
            c = MockHelperClass()
            return c
        plugin = CbaPlugin()
        plugin._get_helper_class = _get_mock_helper_class
        callback_api = MockCallbackApiObject()
        plugin.cba_callback_method(callback_api, 'install_sw', 'COM', 'sc1')

    def test_get_helper_class(self):
        plugin = CbaPlugin()
        for comp in ['COM', 'COMSA', 'JAVAOAM']:
            plugin._get_helper_class(comp)

    def test_cba_callback_method__with_Exc(self):
        def _get_mock_helper_class(comp):
            c = MockHelperClass()
            return c
        plugin = CbaPlugin()
        plugin._get_helper_class = _get_mock_helper_class
        callback_api = MockCallbackApiObject()
        try:
            plugin.cba_callback_method(callback_api,
                                           'install_sw', 'BOGUS', 'sc1')
        except CallbackExecutionException:
            pass

if __name__ == "__main__":
    unittest.main()
