##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from litp.core.litp_logging import LitpLogger
from cbaplugin.file_handler import FileHandler
from cbaplugin.cba_config import CBAConfig
from cbaplugin.cba_base_helper import CbaBaseHelper
from cbaplugin.campaign_runner import CampaignRunner
from cbaplugin.cba_exceptions import CompNotInstalledError
from cbaplugin.cba_exceptions import CompAlreadyInstalledException
from cbaplugin.cba_exceptions import FileHandlerException
from cbaplugin.cba_exceptions import ComSaHelperException
from cbaplugin.cba_exceptions import CBAConfigException
from cbaplugin.cba_exceptions import CommandExecutionError
from cbaplugin.cba_exceptions import CampaignRunnerException
from cbaplugin.cba_constants import (CBA_CFG_FILE,
                                     COMSA_SDP_DIR,
                                     COMSA_PKG_DIR,
                                     COMSA_INSTALL_DIR)
from cbaplugin.cba_utils import recursive_glob
log = LitpLogger()


class ComSaHelper(CbaBaseHelper):
    '''
    ComSaHelper Class is responsible for installing the
    ComSA component on the MN-1 and MN-2 nodes only
    '''

    def __init__(self, plugin):
        '''
        Constructor
        '''
        super(ComSaHelper, self).__init__(plugin)
        self.rstate = None
        self.com_rstate = None
        self.sdp_campaign = None
        self.campaign = None
        self.config = None
        self.tar_files = []
        self.sdp_files = []
        self.comsa_install_sdp = None
        self.comsa_install_sdp_dir = None
        self.comsa_multi_node_dir = None
        self.node_location = None
        self.sdp_file_loc = {}

    def _generate_task(self, plugin_api_context, node_name):
        '''
        This method instructs what the helper class will do,
        currently just installation
        It retrieves the config. process_config may raise an
        exception which is caught by the plugin
        :param plugin_api_context: access to model manager
        :type  plugin_api_context: class
        :param node_name: Name of the Node
        :type  node_name: String
        '''
        task_method = "install_sw"
        task_description = "Install COM-SA Software"
        cba_component = "COMSA"
        self._process_config()
        comsa_pkg = "ERIC-ComSa-CXP9017697_3-" + self.rstate
        try:
            if self._is_component_installed(node_name, comsa_pkg):
                task_method = ''
        except CommandExecutionError as ex:
            log.trace.error("COMSA: Generate_task: exception " + str(ex))
            raise ComSaHelperException("Failed to generate task")

        return task_method, task_description, cba_component

    def do_callback(self, callback_api, method_name, *args, **kwargs):

        '''
        Callback function for the tasks
        :param callback_api: access to security and execution manager
        :type  callback_api: class
        :param method_name: Name of the method to be invoked
        :type  method_name: String
        '''
        log.event.info("COMSA Installing.....")
        func = getattr(self, method_name)
        func(callback_api, args)
        log.event.info("COMSA Installed")

    def install_sw(self, _, node_name):
        '''
        Method contains the body of COMSA Helper.
        All methods that are needed for the installation
        of COMSA are called inside this method

        :param callback_api: access to security and execution manager
        :type  callback_api: class
        :param node_name: Name of the Node
        :type  node_name: String
        '''
        self._process_config()
        self._pre_check(node_name)
        self._prepare_for_install(node_name)
        self._import_campaign(node_name)
        self._execute_campaign(node_name)
        self._post_check()

    def _get_sdps(self):
        '''
        Method will get the sdps file location. It uses recursive_glob
        to search the directory where the tarball was extracted to find
        the sdp file. The resulting list will contain one path if there
        is only one file. It will include the name of the file so that
        is stripped from the end to get the path only
        '''
        #Try will catch the OS exceptions from the recursive glob
        try:
            for sdp in self.sdp_file_loc.keys():
                sdp_path = recursive_glob(COMSA_SDP_DIR, sdp)
                if len(sdp_path) == 1:
                    self.sdp_file_loc[sdp] = sdp_path[0].strip(sdp)
                else:
                    if len(sdp_path) > 1:
                        log.trace.error("Multiple SDP's with the name '%s'"
                                        " found" % sdp)
                    else:
                        log.trace.error("No SDP with the name '%s' found" \
                                         % sdp)
                    raise ComSaHelperException("COMSA Error while getting"
                                                   "  SDP files")
        except ComSaHelperException as ex:
            raise
        except Exception as ex:
            log.trace.error("COMSA: Got an exception getting sdp files"
                            + str(ex))
            raise ComSaHelperException("COMSA :Error finding SDP files "
                                       + str(ex))

    def _pre_check(self, node_name):
        '''
        ensure CMW is instaled
        ensure COM is installed
        ensure COMSA is not installed

        :Param node_name:  Name of the node name
        :type  node_name: String
        '''
        comsa_pkg = "ERIC-ComSa-CXP9017697_3-" + self.rstate
        com_pkg = "ERIC-COM-CXP9017585_3-" + self.com_rstate
        self._is_cmw_ready(node_name)
        if not self._is_component_installed(node_name, com_pkg):
            log.trace.error("COM SDP %s is needed but not installed" % \
                                                                    com_pkg)
            raise CompNotInstalledError("COM component is needed but "
                                                "not installed")
        if self._is_component_installed(node_name, comsa_pkg):
            log.trace.error("COM SA SDP %s is already installed aborting" % \
                                                                    comsa_pkg)
            raise CompAlreadyInstalledException("COM SA component is already"
                                                " installed")

    def _process_config(self):
        '''
        This method instructs the ComSAHelper Class
        to read its configuration from cba_component.conf
        file.
        '''
        try:
            if not self.config:
                self.config = CBAConfig(CBA_CFG_FILE)

            self.rstate = self.config.read_plugin_config('COMSA', 'rstate')
            self.com_rstate = self.config.read_plugin_config('COM', 'rstate')

            self.tar_files.append(
                    self.config.read_plugin_config('COMSA',
                                             'comsa_runtime_tar')
                                            .replace("<rstate>", self.rstate))

            self.tar_files.append(
                    self.config.read_plugin_config('COMSA',
                                            'comsa_template_tar')
                                            .replace("<rstate>", self.rstate))

            sdp_file = self.config.read_plugin_config("COMSA", "comsa_sdp")
            self.sdp_files.append(sdp_file)
            #Creating dict so location can be store in it later for this key
            self.sdp_file_loc.update({sdp_file: ""})

            self.comsa_install_sdp = self.config.read_plugin_config("COMSA",
                                             "comsa_install_sdp")

            self.comsa_install_sdp_dir = self.config.read_plugin_config(
                                "COMSA",  "comsa_install_sdp_dir").replace(
                                            "<rstate>", self.rstate)
        except CBAConfigException as ex:
            log.trace.error("COMSA-process_config: failed to read config, "
                            "got exception " + str(ex))
            raise ComSaHelperException("process_config: failed to read config")

    def _prepare_for_install(self, node_name):
        '''
        Untar the tar files, get location of the sdp files
        and transfer them to the node

        :param node_name: name of the node
        :type  node_name: String
        '''
        try:
            # Untar the  tar files
            fh = FileHandler("COMSA", COMSA_PKG_DIR, COMSA_SDP_DIR)
            for tar_file in self.tar_files:
                fh.untar_file(tar_file)
        except FileHandlerException as ex:
            fh.clean_sdp_install_dir()
            log.trace.error("COMSA Untaring tarballs failed" + str(ex))
            raise ComSaHelperException("COMSA Untaring tarballs failed" \
                                     + str(ex))
        try:
            self._get_sdps()
            self.sdp_files.append(self.comsa_install_sdp)
            self.node_location = COMSA_SDP_DIR + '/' \
                            + self.comsa_install_sdp_dir
            self.sdp_file_loc.update({self.comsa_install_sdp: \
                                         self.node_location})
            #Transfer the files to Primary node
            self.campaign = CampaignRunner(node_name, COMSA_INSTALL_DIR)
            for sdp_file in self.sdp_files:
                sdp_loc = self.sdp_file_loc[sdp_file]
                log.trace.info("COMSA: Transfering %s from location %s"
                                    % (sdp_file, sdp_loc))
                self.campaign.transfer_sdp(sdp_loc, sdp_file)
            fh.clean_sdp_install_dir()
        except  CampaignRunnerException as ex:
            log.trace.error("COMSA: prepare_for_install, failed to transfer "
                            "sdps. got exception " + str(ex))
            raise ComSaHelperException("prepare_for_install: Got exception: "
                                     + str(ex))

    def _import_campaign(self, _):
        '''
        This method instructs the ComSaHelper Class
        to import the campaigns.
        '''
        try:
            for sdp_file in self.sdp_files:
                log.trace.info("COM: Import Campaign run on %s"
                                    % (sdp_file))
                self.campaign.import_sdp(sdp_file)
        except CampaignRunnerException as ex:
            log.trace.error("COMSA: _import_campaign, failed to import "
                            " sdps. got exception " + str(ex))
            raise ComSaHelperException("_import_campaign: Got exception: "
                                     + str(ex))

    def _execute_campaign(self, _):
        '''
        This method instructs the ComSaHelper Class
        to run the campaigns.
        '''
        try:
            self.campaign.execute_campaign("ERIC-ComSaInstall")
        except CampaignRunnerException as ex:
            log.trace.error("COMSA:_execute_campaign, failed to execution "
                            " campaign. got exception " + str(ex))
            raise ComSaHelperException("_execute_campaign: Got exception: "
                                     + str(ex))

    def _post_check(self):
        pass

#############################################################################
#Section below is only for testing COMSA outside the cbaplugin
#if __name__ == "__main__":
#    ch = ComSaHelper(None)
#    ch.do_callback(None, "install_sw", "mn1")
#'''
