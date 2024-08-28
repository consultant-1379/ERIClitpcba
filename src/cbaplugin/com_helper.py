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
from cbaplugin.cba_exceptions import CompAlreadyInstalledException
from cbaplugin.cba_exceptions import ComHelperException
from cbaplugin.cba_exceptions import CBAConfigException
from cbaplugin.cba_exceptions import CommandExecutionError
from cbaplugin.cba_exceptions import CampaignRunnerException
from cbaplugin.cba_constants import (CBA_CFG_FILE,
                                     COM_SDP_DIR,
                                     COM_PKG_DIR,
                                     COM_INSTALL_DIR)
from cbaplugin.cba_utils import recursive_glob
log = LitpLogger()


class ComHelper(CbaBaseHelper):
    '''
    ComHelper Class is responsible for installing the
    Com component on the MN-1 and MN-2 nodes
    '''

    def __init__(self, plugin):
        '''
        Constructor
        '''
        super(ComHelper, self).__init__(plugin)
        self.rstate = None
        self.campaign = None
        self.config = None
        self.tar_files = []
        self.sdp_files = []
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
        task_description = "Install COM Software"
        cba_component = "COM"
        self._process_config()
        com_pkg = "ERIC-COM-CXP9017585_3-" + self.rstate
        try:
            if self._is_component_installed(node_name, com_pkg):
                task_method = ''
        except CommandExecutionError as ex:
            log.trace.error("generate_task: exception " + str(ex))
            raise ComHelperException("Failed to generate task")

        log.trace.info("generate_task: install_sw task created for ComHelper")
        return task_method, task_description, cba_component

    def do_callback(self, callback_api, method_name, *args, **kwargs):
        '''
        Callback function for the tasks
        :param callback_api: access to security and execution manager
        :type  callback_api: class
        :param method_name: Name of the method to be invoked
        :type  method_name: String
        '''
        log.event.info("COM Installing.......")
        func = getattr(self, method_name)
        func(callback_api, args)
        log.event.info("COM Installed")

    def install_sw(self, _, node_name):
        '''
        Method contains the body of COM Helper.
        All methods that are needed for the installation
        of COM are called inside this method

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

    def _process_config(self):
        '''
        This method instructs the ComHelper Class
        to read its configuration from cba_component.conf
        file.
        '''
        try:
            if not self.config:
                self.config = CBAConfig(CBA_CFG_FILE)

            self.rstate = self.config.read_plugin_config("COM", "rstate")
            tarfile = self.config.read_plugin_config("COM", "com_tar")
            tarfile = tarfile.replace("<rstate>", self.rstate)
            self.tar_files.append(tarfile)

            tarfile = self.config.read_plugin_config("COM", "com_template_tar")
            tarfile = tarfile.replace("<rstate>", self.rstate)
            self.tar_files.append(tarfile)

            sdp_file = self.config.read_plugin_config("COM", "com_sdp")
            self.sdp_files.append(sdp_file)
            self.sdp_file_loc.update({sdp_file: ""})
            sdp_file = self.config.read_plugin_config("COM",
                "com_multi_node_template")
            sdp_file = sdp_file.replace("<rstate>", self.rstate)
            self.sdp_files.append(sdp_file)
            self.sdp_file_loc.update({sdp_file: ""})
        except CBAConfigException as ex:
            log.trace.error("process_config: failed to read config, "
                            "got exception " + str(ex))
            raise ComHelperException("process_config: failed to read config")

    def _get_sdps(self):
        '''
        Method will get the sdps file location. It uses recursive_glob
        to search the directory where the tarball was extracted to find
        the sdp file. The resulting list will contain one path if there
        is only one file. It will include the name of the file so that
        is stripped from the end to get the path only
        '''
        try:
            for sdp in self.sdp_file_loc.keys():
                sdp_path = recursive_glob(COM_SDP_DIR, sdp)
                if len(sdp_path) == 1:
                    self.sdp_file_loc[sdp] = sdp_path[0].strip(sdp)
                else:
                    if len(sdp_path) > 1:
                        log.trace.error("Multiple SDP's with the name '%s'"
                                        " found" % sdp)
                    else:
                        log.trace.error("No SDP with the name '%s'"
                                        " found" % sdp)
                    raise ComHelperException("Error while getting SDP files")
        except Exception as ex:
            log.trace.error("get_sdps: got exception trying to find sdps "
                            + str(ex))
            raise ComHelperException("Error finding SDP files")

    def _pre_check(self, node_hostname):
        '''
        ensure CMW is installed
        ensure COM is not installed
        ensure COMSA is not installed

        :param node_name: Name of the node name
        :type  node_name: String
        '''
        self._is_cmw_ready(node_hostname)

        com_pkg = "ERIC-COM-CXP9017585_3-" + self.rstate

        if self._is_component_installed(node_hostname, com_pkg):
            log.trace.error("COM SDP %s is already installed aborting" % \
                                                                    com_pkg)
            raise CompAlreadyInstalledException("COM component is already"
                                                " installed")

    def _prepare_for_install(self, node_name):
        '''
        This method will untar the needed tar files
        and transfer the correct sdps to the specified node

        :param node_name: name of the node
        :type  node_name: String
        '''
        try:
            fh = FileHandler("COM", COM_PKG_DIR, COM_SDP_DIR)
            for tar_file in self.tar_files:
                log.trace.info("COM: untaring %s" % (tar_file))
                fh.untar_file(tar_file)
            self._get_sdps()
            self.campaign = CampaignRunner(node_name, COM_INSTALL_DIR)
            for sdp_file in self.sdp_files:
                sdp_loc = self.sdp_file_loc[sdp_file]
                log.trace.info("COM: Transfering %s from location %s"
                                    % (sdp_file, sdp_loc))
                self.campaign.transfer_sdp(sdp_loc, sdp_file)
            fh.clean_sdp_install_dir()
        except CampaignRunnerException as ex:
            log.trace.error("prepare_for_install, failed to transfer "
                            "sdps. got exception " + str(ex))
            raise ComHelperException("prepare_for_install: Got exception: "
                                     + str(ex))

    def _import_campaign(self, _):
        '''
        Calls the Import campaign method from
        the campaign runner.  The campaign runner will
        run the import command

        :param node_name: Name of the node
        :type  node_name: String,
        '''
        try:
            for sdp_file in self.sdp_files:
                log.trace.info("COM: Import Campaign run on %s"
                                    % (sdp_file))
                self.campaign.import_sdp(sdp_file)
        except CampaignRunnerException as ex:
            log.trace.error("_import_campaign, failed to import "
                            "sdps. got exception " + str(ex))
            raise ComHelperException("_import_campaign: Got exception: "
                                     + str(ex))

    def _execute_campaign(self, _):
        '''
        Calls the execute campaign method from
        the campaign runner.  The campaign runner will
        run the execute command

        :param node_name: name of the node
        :type  node_name: String
        '''
        try:
            sdp_campaign = self.config.read_plugin_config('COM',
                                         'com_multi_node_template')
            sdp_campaign = sdp_campaign.replace("<rstate>",
                                                          self.rstate)
            sdp_campaign = sdp_campaign.strip(".sdp")
            log.trace.info("COM: Execute Campaign on %s"
                                    % (sdp_campaign))
            self.campaign.execute_campaign(sdp_campaign)
        except CampaignRunnerException as ex:
            log.trace.error("_execute_campaign, failed to execution "
                            "campaign. got exception " + str(ex))
            raise ComHelperException("_execute_campaign: Got exception: "
                                     + str(ex))

    def _post_check(self):
        '''
        Runs a post check command on COM
        to ensure its installed correctly
        '''
        log.trace.info("COM: precheck command '/opt/com/bin/cliss --h' ran")
        retcode, _ = self.campaign._execute_cmd("/opt/com/bin/cliss --h")
        if not retcode == 0:
            log.trace.error("COM: precheck command '/opt/com/bin/cliss --h' \
                             failed")
            raise ComHelperException("COM: precheck command  failed")
