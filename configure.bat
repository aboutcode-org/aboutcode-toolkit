@echo OFF
@rem Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.

set ABOUT_ROOT_DIR=%~dp0

set CFG_CMD_LINE_ARGS= 
@rem Collect all command line arguments in a variable
:collectarg
 if ""%1""=="""" goto continue
 call set CFG_CMD_LINE_ARGS=%CFG_CMD_LINE_ARGS% %1
 shift
 goto collectarg

:continue

@rem default configuration when no args are passed
if "%CFG_CMD_LINE_ARGS%"==" " (
    set CFG_CMD_LINE_ARGS=etc/conf
    goto configure
)

:configure
call %ABOUT_ROOT_DIR%\etc\configure %CFG_CMD_LINE_ARGS%
goto EOS

:EOS