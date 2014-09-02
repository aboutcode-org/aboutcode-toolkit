@echo OFF
@rem  Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.
@rem  


@rem  cd to the dpl directory
set ROOT_DIR=%~dp0
cd %ROOT_DIR%

set CMD_LINE_ARGS= 
set CONFIGURED_PYTHON=%ROOT_DIR%\Scripts\python.exe

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
 call %ROOT_DIR%\configure

:about
call %ROOT_DIR%\Scripts\activate
%ROOT_DIR%\bin\about-code %DPL_CMD_LINE_ARGS%

:EOS
