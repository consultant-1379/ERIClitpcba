##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################


class JavaOamHelperException(Exception):
    pass


class CbaHelperException(Exception):
    pass


class UnknownCbaCompException(Exception):
    pass


class CommandExecutionError(Exception):
    pass


class CompAlreadyInstalledException(Exception):
    pass


class CompNotInstalledError(Exception):
    pass


class CMWStateError(Exception):
    pass


class CBAConfigException(Exception):
    pass


class CampaignRunnerException(Exception):
    pass


class ComSaHelperException(Exception):
    pass


class ComHelperException(Exception):
    pass


class FileHandlerException(Exception):
    pass
