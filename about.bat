@echo OFF
@rem  Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
@rem  


@rem  cd to the dpl directory
set ABOUT_ROOT_DIR=%~dp0
cd %ABOUT_ROOT_DIR%

# where we create a virtualenv
set VIRTUALENV_DIR=venv

set CMD_LINE_ARGS= 
set CONFIGURED_PYTHON="%ABOUT_ROOT_DIR%\%VIRTUALENV_DIR%\Scripts\python.exe"

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
 call "%ABOUT_ROOT_DIR%\configure"

:about
call "%ABOUT_ROOT_DIR%\%VIRTUALENV_DIR%\Scripts\activate"
echo "%ABOUT_ROOT_DIR%\%VIRTUALENV_DIR%\bin\about" %CMD_LINE_ARGS%
"%ABOUT_ROOT_DIR%\%VIRTUALENV_DIR%\bin\about" %CMD_LINE_ARGS%

:EOS
