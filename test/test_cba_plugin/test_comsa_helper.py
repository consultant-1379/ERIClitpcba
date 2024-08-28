##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

#from cbaplugin.cba_utils import recursive_glob
from cbaplugin.com_sa_helper import ComSaHelper
from cbaplugin.com_sa_helper import ComSaHelperException
import ConfigParser
from StringIO import StringIO
from cbaplugin import cba_config
from cbaplugin.cba_exceptions import CompAlreadyInstalledException
from cbaplugin.cba_exceptions import CompNotInstalledError
from cbaplugin.cba_config import CBAConfigException
from cbaplugin.file_handler import FileHandlerException
from cbaplugin.campaign_runner import CampaignRunner

import unittest
import mock
from mock import Mock

default_config = """
[COMSA]
rstate=R4C02
comsa_runtime_tar=COM_SA_RUNTIME-<rstate>.tar
comsa_template_tar=COM_SA_D_TEMPLATE-<rstate>.tar.gz
comsa_sdp=COM_SA-CXP9017697_3.sdp
comsa_install_sdp=ComSa_install.sdp
comsa_install_sdp_dir=COM_SA_I1_TEMPLATE-CXP9018914_3-<rstate>
[COM]
rstate=R1A02
"""


class MockCBAConfig(object):
    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(StringIO(default_config))

    def read_plugin_config(self, section, option):
        value = self.config.get(section, option)
        return value


def recursive_glob_side_effect(treeroot, pattern):
    return ['/tmpdir/comsa.sdp']


def recursive_glob_side_effect_multi(treeroot, pattern):
    return ['/tmpdir/test_sdp.sdp', '/tmpdir/test_sdp2.sdp']


def campaign_execute_cmd_side_effect(self, cmd):
    print cmd
    return (0, "Status OK")


def component_installed(node, sdp):
    if sdp.startswith("ERIC-ComSa"):
        return False
    else:
        return True


class TestComSaHelper(unittest.TestCase):

    def setUp(self):
        self.comSaHelper = ComSaHelper(None)
        self.comSaHelper.config = ConfigParser.ConfigParser()
        self.comSaHelper.config.readfp(StringIO(default_config))
        self.comSaHelper.config = MockCBAConfig()

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_component_installed', mock.MagicMock(return_value=False))
    def test_generate_task_successfully(self):
        result = self.comSaHelper._generate_task(None, None)
        self.assertEquals(result, ("install_sw", "Install COM-SA Software",
                                   "COMSA"))

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_component_installed', mock.MagicMock(return_value=True))
    def test_generate_task_unsuccessfully(self):
        result = self.comSaHelper._generate_task(None, None)
        self.assertEquals(result, ("", "Install COM-SA Software",
                                   "COMSA"))

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_component_installed',
                  mock.MagicMock(side_effect=component_installed))
    @mock.patch('cbaplugin.com_sa_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect))
    @mock.patch('cbaplugin.file_handler.FileHandler.untar_file',
                mock.MagicMock())
    @mock.patch('cbaplugin.file_handler.FileHandler.clean_sdp_install_dir',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.transfer_sdp',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.import_sdp',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.execute_campaign',
                mock.MagicMock())
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_cmw_ready',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner._execute_cmd',
                mock.MagicMock(side_effect=campaign_execute_cmd_side_effect))
    def test_do_callback_success(self):
        self.comSaHelper.do_callback(None, "install_sw", "mn1")

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_component_installed',
                  mock.MagicMock(return_value=True))
    @mock.patch('cbaplugin.com_sa_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect))
    @mock.patch('cbaplugin.file_handler.FileHandler.untar_file',
                mock.MagicMock())
    @mock.patch('cbaplugin.file_handler.FileHandler.clean_sdp_install_dir',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.transfer_sdp',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.import_sdp',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.execute_campaign',
                mock.MagicMock())
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_cmw_ready',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner._execute_cmd',
                mock.MagicMock(side_effect=campaign_execute_cmd_side_effect))
    def test_do_callback_fails(self):
        try:
            self.comSaHelper.do_callback(None, "install_sw", "mn1")
        except CompAlreadyInstalledException as error:
            self.assertEquals("COM SA component is already installed", str(error))

    @mock.patch('cbaplugin.com_sa_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect))
    def test_get_sdp_successfully(self):
        self.comSaHelper._process_config()
        self.comSaHelper._get_sdps()
        self.assertEquals(self.comSaHelper.sdp_file_loc.values()[0], '/tmpdir/comsa')

    @mock.patch('cbaplugin.com_sa_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect_multi))
    def test_get_sdps_neg_multiple_sdps(self):
        self.comSaHelper._process_config()
        self.assertRaises(ComSaHelperException, self.comSaHelper._get_sdps)

    def test_get_sdps_unsuccessfully(self):
        self.comSaHelper._process_config()
        try:
            self.comSaHelper._get_sdps()
        except ComSaHelperException as error:
            self.assertEquals("COMSA Error while getting  SDP files",
                                  str(error))

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_component_installed',
                  mock.MagicMock(side_effect=component_installed))
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_cmw_ready', mock.MagicMock())
    def test_pre_check_successfully(self):
        self.comSaHelper._process_config()
        self.comSaHelper._pre_check("mn1")

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_component_installed',
                  mock.MagicMock(return_value=False))
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_cmw_ready', mock.MagicMock())
    def test_pre_check_fails_for_com_install_check(self):
        self.comSaHelper._process_config()
        try:
            self.comSaHelper._pre_check("mn1")
        except CompNotInstalledError as error:
            self.assertEquals("COM component is needed but not installed", str(error))

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_component_installed',
                  mock.MagicMock(return_value=True))
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_cmw_ready', mock.MagicMock())
    def test_pre_check_fails_for_comsa(self):
        self.comSaHelper._process_config()
        try:
            self.comSaHelper._pre_check("mn1")
        except CompAlreadyInstalledException as error:
            self.assertEquals("COM SA component is already installed", str(error))

























#    @mock.patch('cbaplugin.com_sa_helper.recursive_glob',
#                mock.MagicMock(return_value="blah"))
#    def test_get_sdps(self):
#        self.ch.sdp_files["a"] = "aaaa"
#        self.ch.sdp_files["b"] = "bbbb"
#        self.ch._get_sdps()

#    def test_pre_check(self):
#        pass

#    def test_prepare_for_install(self):
#        pass

#    def test_import_campaign(self):
#        pass

#    def test_execute_campaign(self):
#        pass

#    def test_post_check(self):
#        pass
