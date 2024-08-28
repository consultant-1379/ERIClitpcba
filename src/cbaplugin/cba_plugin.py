##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################


from cbaplugin.com_helper import ComHelper
from cbaplugin.com_sa_helper import ComSaHelper
from cbaplugin.java_oam_helper import JavaOamHelper
from cbaplugin.cba_exceptions import UnknownCbaCompException

from litp.core.plugin import Plugin
from litp.core.litp_logging import LitpLogger
from litp.core.execution_manager import CallbackExecutionException
log = LitpLogger()

COMPONENTS = ['COM', 'COMSA', 'JAVAOAM']


class CbaPlugin(Plugin):
    """
    This plugin is responsible for the installation/upgrading/configuration
    of CBA software including:
    * COM
    * COMSA
    * JAVAOAM
    * MMAS
    The need for the installation of this software is inferred from the litp
    model. If a jboss-runtime item is presnet within a cmw-clister then the
    installation/upgrade is triggered.
    """

    def validate_model(self, plugin_api_context):
        """
        No validation of the model is required
        """
        errors = []
        return errors

    def _get_helper_class(self, comp):
        c = None
        if comp == 'COM':
            c = ComHelper(CbaPlugin)
        elif comp == 'COMSA':
            c = ComSaHelper(CbaPlugin)
        elif comp == 'JAVAOAM':
            c = JavaOamHelper(CbaPlugin)
        return c

    def create_configuration(self, plugin_api_context):
        """
        Create Tasks for CBA Components. This method will check the model and
        nodes to see what tasks are required to install/upgrade/configure CBA
        software.
        """
        tasks = []
        clusters = plugin_api_context.query("cmw-cluster")
        for cluster in clusters:
            if cluster.query('jboss-runtime'):
                for comp in COMPONENTS:
                    tasks.extend(self._get_helper_class(comp).\
                                      create_configuration(plugin_api_context,
                                                           cluster))
        return tasks

    def cba_callback_method(self,
                            callback_api,
                            method_name,
                            cba_component,
                            primary_node_name,
                            *args,
                            **kwargs):
        """
        This method executes the required method in the appropiate helper class
        :param callback_api: CallbackApi instance.
        :type  callback_api: CallbackApi
        :param method_name: Name of the method that is to be executed
        :type  method_name: string
        :param cba_component: Name of CBA component
        :type  cba_component: string
        :param primary_node_name: Hostname of CMW's first controller node
        :type  primary_node_name: string
        """
        try:
            if cba_component in COMPONENTS:
                log.trace.info('Checking for tasks for CBA Software: %s'\
                                                  % cba_component)
                self._get_helper_class(cba_component).do_callback(
                    callback_api,
                    method_name,
                    primary_node_name,
                    *args, **kwargs)
            else:
                raise UnknownCbaCompException(
                        "%s is not a recognised CBA Component" % cba_component)
        except Exception as ex:
            log.trace.error("cba_callback_method: Exception occurred during "
                            "execution of callback " + str(ex))
            raise CallbackExecutionException("cba_callback_method: Exception "
                                             "occurred during execution of "
                                             "callback " + str(ex))
