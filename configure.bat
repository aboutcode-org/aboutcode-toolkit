@echo OFF

@rem Copyright (c) 2015 nexB Inc. http://www.nexb.com/ - All rights reserved.

@rem ################################
@rem # change these variables to customize this script locally
@rem ################################
@rem # you can define one or more thirdparty dirs, each prefixed with TPP_DIR
set TPP_DIR=thirdparty


@rem # default configurations
set CONF_DEFAULT="etc/conf"
@rem #################################

set CFG_CMD_LINE_ARGS= 
@rem Collect/Slurp all command line arguments in a variable
:collectarg
 if ""%1""=="""" (
    goto continue
 )
 call set CFG_CMD_LINE_ARGS=%CFG_CMD_LINE_ARGS% %1
 shift
 goto collectarg

:continue

@rem default configuration when no args are passed
if "%CFG_CMD_LINE_ARGS%"==" " (
    set CFG_CMD_LINE_ARGS="%CONF_DEFAULT%"
    goto configure
)

if "%CFG_CMD_LINE_ARGS%"=="  --init" (
    set CFG_CMD_LINE_ARGS="%CONF_INIT%"
    goto configure
)

:configure
call c:\Python27\python.exe etc/configure.py %CFG_CMD_LINE_ARGS%
if exist bin\activate (
    bin\activate
)
goto EOS

:EOS
