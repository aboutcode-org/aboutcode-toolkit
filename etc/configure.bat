@echo OFF
@rem Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.
@rem

@rem std python
set PYTHON="c:\Python27\python.exe"

@rem ROOT_DIR must have been set by the calling script

set CONFIGURED_PYTHON=%ROOT_DIR%\Scripts\python.exe

if "%1"=="--clean" goto clean

@rem create bin dir
if not exist %ROOT_DIR%\bin mkdir %ROOT_DIR%\bin

set CMD_LINE_ARGS= 
@rem Collect all command line arguments in a variable
:collectarg
 if ""%1""=="""" goto continue
 call set CMD_LINE_ARGS=%CMD_LINE_ARGS% %1
 shift
 goto collectarg

:continue

if exist %CONFIGURED_PYTHON% goto pip_requirement

@rem Install and activate a virtualenv without any download
echo.
echo * Configuring Python ...
"%PYTHON%" %ROOT_DIR%\thirdparty\virtualenv.py --never-download --extra-search-dir=%ROOT_DIR%\thirdparty\ %ROOT_DIR%


:pip_requirement

call %ROOT_DIR%\Scripts\activate.bat

echo.
echo * Installing components ...
@rem Install components from selected requirements
%CONFIGURED_PYTHON% %ROOT_DIR%\etc\getconf.py --requirements %CMD_LINE_ARGS%> tmpreqfile
for /F %%i in (tmpreqfile) do (
    pip install --upgrade --no-index --no-allow-external --use-wheel --find-links=%ROOT_DIR%\thirdparty\ -r %ROOT_DIR%\%%i
)
del tmpreqfile > NUL

echo.
echo * Configuring ...
:scripts
@rem Run selected configuration python scripts
%CONFIGURED_PYTHON% %ROOT_DIR%\etc\getconf.py --python %CMD_LINE_ARGS% > tmppyfile
for /F %%i in (tmppyfile) do (
    %CONFIGURED_PYTHON% %ROOT_DIR%\%%i
)
del tmppyfile > NUL


@rem Run selected configuration bat scripts
%CONFIGURED_PYTHON% %ROOT_DIR%\etc\getconf.py --shell %CMD_LINE_ARGS% > tmpscrfile
for /F %%i in (tmpscrfile) do (
    call %ROOT_DIR%\%%i
)
del tmpscrfile > NUL

goto EOS

:clean
echo * Cleaning ...
if exist %ROOT_DIR%\Scripts\deactivate.bat call %ROOT_DIR%\Scripts\deactivate
cd %ROOT_DIR%
rmdir /S /Q bin build Scripts Lib Include 2>NUL
goto EOS


:EOS