@echo OFF
@rem  Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.
@rem  


@rem  cd to the dpl directory
set ABOUT_ROOT_DIR=%~dp0
cd %ABOUT_ROOT_DIR%

set CMD_LINE_ARGS= 
set CONFIGURED_PYTHON=%ABOUT_ROOT_DIR%\Scripts\python.exe

@rem Collect all command line arguments in a variable
:collectarg
 if ""%1""=="""" goto continue
 call set CMD_LINE_ARGS=%CMD_LINE_ARGS% %1
 shift
 goto collectarg

:continue


if not exist %CONFIGURED_PYTHON% goto configure
goto about

:configure
 echo * Configuring AboutCode ...
 call %ABOUT_ROOT_DIR%\configure

:about
call %ABOUT_ROOT_DIR%\Scripts\activate
echo %ABOUT_ROOT_DIR%\bin\about-code %CMD_LINE_ARGS%
%ABOUT_ROOT_DIR%\bin\about-code %CMD_LINE_ARGS%

:EOS
