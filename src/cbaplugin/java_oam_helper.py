##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import tempfile

from litp.core.litp_logging import LitpLogger
from cbaplugin import cba_constants
log = LitpLogger()

from cbaplugin.cba_config import CBAConfig
from cbaplugin.cba_base_helper import CbaBaseHelper
from cbaplugin.file_handler import FileHandler
from cbaplugin.cba_utils import recursive_glob
from cbaplugin.cba_exceptions import FileHandlerException
from cbaplugin.cba_exceptions import JavaOamHelperException
from cbaplugin.cba_exceptions import CompAlreadyInstalledException
from cbaplugin.cba_exceptions import CompNotInstalledError
from cbaplugin.cba_exceptions import CommandExecutionError


class JavaOamHelper(CbaBaseHelper):
    """
    This class is responsible to parse and prepare information for
    JavaOaM install and upgrades.
    """

    def __init__(self, plugin):
        """ Constructor
        :param plugin: Plugin class
        :type plugin: class
        """
        super(JavaOamHelper, self).__init__(plugin)
        self.config = None
        self.action = "install"
        self.rstate = ""
        self.sdp_dir = tempfile.mkdtemp()
        self.tar_files = []
        self.sdp_files = {}
        self.campaign_name = None

    def _generate_task(self, plugin_api_context, node_hostname):
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
        # TODO validate what exactly need to be called install or upgrade
        task_method = "install_sw"
        task_description = "Install JavaOaM Software"
        cba_comp = "JAVAOAM"
        self._process_config()
        # TODO: we will need to check versions in the future.
        try:
            if self._is_component_installed(node_hostname,
                                     cba_constants.JAVAOAM_MAIN_SDP):
                task_method = ''
        except CommandExecutionError as ex:
            log.trace.error("JavaOam: Generate_task: exception " + str(ex))
            raise JavaOamHelperException("Failed to generate task")

        return task_method, task_description, cba_comp

    def do_callback(self, callback_api,
                          method_name,
                          node_hostname,
                          *args, **kwargs):
        '''
        Callback function for the tasks
        :param callback_api: access to security and execution manager
        :type  callback_api: class
        :param method_name: Name of the method to be invoked
        :type  method_name: String
        '''
        log.event.info("JavaOAM Installing.....")
        func = getattr(self, method_name)
        func(callback_api, node_hostname)
        log.event.info("JavaOaM Installed")

    def install_sw(self, _, node_hostname):
        '''
        Method contains the body of JavaOAM Helper.
        All methods that are needed for the installation
        of JavaOAM are called inside this method

        :param callback_api: access to security and execution manager
        :type  callback_api: class
        :param node_name: Name of the Node
        :type  node_name: String
        '''
        self._process_config()
        self._pre_check(node_hostname)
        self._prepare_for_install(node_hostname)
        self._import_campaign(node_hostname)
        self._execute_campaign(node_hostname)
        self._post_check()

    def _pre_check(self, node_hostname):
        """ Pre callback execution checks
        """
        #TODO check versions in the future
        self._is_cmw_ready(node_hostname)
        if self._is_component_installed(node_hostname,
                                        cba_constants.JAVAOAM_MAIN_SDP):
            log.trace.error("JavaOaM SDP %s is already installed, aborting" %\
                                                cba_constants.JAVAOAM_MAIN_SDP)
            raise CompAlreadyInstalledException("JavaOaM is already installed")
        if not self._is_component_installed(node_hostname,
                                            cba_constants.COM_MAIN_SDP):
            log.trace.error("COM SDP %s is needed but not installed,"
                            " aborting" % cba_constants.COM_MAIN_SDP)
            raise CompNotInstalledError("COM component needs to be installed"
                                        " for JavaOaM")
        if not self._is_component_installed(node_hostname,
                                                cba_constants.COM_SA_MAIN_SDP):
            log.trace.error("COM SA SDP %s is needed but not installed,"
                            " aborting" % cba_constants.COM_SA_MAIN_SDP)
            raise CompNotInstalledError("ComSa component needs to be installed"
                                        " for JavaOaM")

    def _prepare_for_install(self, _):
        self._unpack_tarballs()
        self._get_sdps()

    def _process_config(self):
        '''
        This method instructs the JavaOAM Helper Class
        to read its configuration from cba_component.conf
        file.
        '''
        try:
            if not self.config:
                self.config = CBAConfig()
            self.rstate = self.config.read_plugin_config("JAVAOAM", "rstate")
            self.tar_files.append(
                    self.config.read_plugin_config("JAVAOAM", "javaoam_tar").\
                                                            replace("<rstate>",
                                                                 self.rstate))
            self.tar_files.append(
                    self.config.read_plugin_config("JAVAOAM",
                                        "javaoam_template_tar").replace(
                                                                    "<rstate>",
                                                                  self.rstate))
            sdp_list = self.config.read_plugin_config("JAVAOAM",
                                                      "javaoam_sdps")
            for sdp in sdp_list.split(","):
                self.sdp_files[sdp.strip().replace("<rstate>",
                                                   self.rstate)] = ""
            template = self.config.read_plugin_config("JAVAOAM",
                                                 "javaoam_{0}_template".format(
                                                                  self.action))
            self.sdp_files[template] = ""
            # SDP filename needs to match the campaign name for SMF to accept
            # it so we can trust the filename here
            self.campaign_name = template.strip(".sdp")
        except:
            log.event.error("Reading config file for CBA plugin failed")
            raise JavaOamHelperException("Error while reading config file")

    def _unpack_tarballs(self):
        try:
            tar_dir = cba_constants.JAVAOAM_PKG_DIR
            fh = FileHandler("JavaOaM", tar_dir, self.sdp_dir)
            for tar_file in self.tar_files:
                fh.untar_file(tar_file)
        except FileHandlerException as ex:
            log.trace.error("JavaOam Untaring tarballs failed" + str(ex))
            raise JavaOamHelperException("JavaOam Untaring tarballs failed" \
                                     + str(ex))

    def _get_sdps(self):
        '''
        Method will get the sdps file location. It uses recursive_glob
        to search the directory where the tarball was extracted to find
        the sdp file. The resulting list will contain one path if there
        is only one file. It will include the name of the file so that
        is stripped from the end to get the path only
        '''
        try:
            for sdp in self.sdp_files.keys():
                sdp_path = recursive_glob(self.sdp_dir, sdp)
                if len(sdp_path) == 1:
                    self.sdp_files[sdp] = sdp_path[0]
                else:
                    if len(sdp_path) > 1:
                        log.trace.error("Multiple SDP's with the name '%s' "
                                                     "found" % sdp)
                        raise JavaOamHelperException("Error while getting SDP "
                                                     "files")
                    else:
                        log.trace.error("No SDP with the name '%s' found" \
                                                              % sdp)
                    raise JavaOamHelperException("Error while getting SDP "
                                                       "files")
        except JavaOamHelperException as ex:
            raise
        except Exception as ex:
            log.trace.error("JavaOam: Got an exception getting sdp files"
                            + str(ex))
            raise JavaOamHelperException("JavaOam :Error finding SDP files "
                                       + str(ex))
