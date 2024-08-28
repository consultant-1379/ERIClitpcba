##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import ConfigParser
import unittest
from StringIO import StringIO

from cbaplugin import cba_config
from cbaplugin.cba_exceptions import CBAConfigException

sample_config = """
[JAVAOAM]
javaoam_tar=JAVAOAM_RUNTIME_CXP9020490_1_<rstate>.tar.gz
javaoam_template_tar=JAVAOAM_D_TEMPLATE_CXP9020489_1_<rstate>.tar.gz
rstate=R3A18
javaoam_sdps=ERIC-JAVAOAM_CORE-CXP9030376_1-<rstate>.sdp,ERIC-JAVAOAM_LMCLIENT-CXP9030377_1-<rstate>.sdp
javaoam_install_template=ERIC-JAVAOAM-I-2SCxNPL.sdp
javaoam_upgrade_template=ERIC-JAVAOAM-U-2SCxNPL_TEMPLATE.sdp
javaoam_remove_template=
"""


class MockCBAConfig(cba_config.CBAConfig):
    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(StringIO(sample_config))


class TestCBAConfig(unittest.TestCase):

    def setUp(self):
        self.cbaconfig = MockCBAConfig()

    def test_read_config(self):
        tar = self.cbaconfig.read_plugin_config("JAVAOAM", "javaoam_tar")
        self.assertEquals(tar, "JAVAOAM_RUNTIME_CXP9020490_1_<rstate>.tar.gz")
        self.assertRaises(CBAConfigException,
                        self.cbaconfig.read_plugin_config, "JAVAOAM", "blabla")
        self.assertRaises(CBAConfigException,
                        self.cbaconfig.read_plugin_config, "JAVAOAM",
                        "javaoam_remove_template")

    def test_cba_config(self):
        self.assertRaises(CBAConfigException, cba_config.CBAConfig)
