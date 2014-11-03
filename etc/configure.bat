@echo OFF
@rem Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.
@rem

@rem std python
set PYTHON="c:\Python27\python.exe"

@rem ABOUT_ROOT_DIR must have been set by the calling script

cd %ABOUT_ROOT_DIR%

set CONFIGURED_PYTHON=%ABOUT_ROOT_DIR%\Scripts\python.exe

if "%1"=="--clean" goto clean

@rem create Scripts dir
if not exist %ABOUT_ROOT_DIR%\Scripts mkdir %ABOUT_ROOT_DIR%\Scripts
@rem Link bin dir as Junction (aka Symbolic link)
if not exist %ABOUT_ROOT_DIR%\bin (
    mklink /J %ABOUT_ROOT_DIR%\bin %ABOUT_ROOT_DIR%\Scripts
)

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
"%PYTHON%" %ABOUT_ROOT_DIR%\thirdparty\virtualenv.py --never-download --extra-search-dir=%ABOUT_ROOT_DIR%\thirdparty\ %ABOUT_ROOT_DIR%


:pip_requirement

call %ABOUT_ROOT_DIR%\Scripts\activate.bat

echo.
echo * Installing components ...
@rem Install components from selected requirements
%CONFIGURED_PYTHON% %ABOUT_ROOT_DIR%\etc\getconf.py --requirements %CMD_LINE_ARGS%> tmpreqfile
for /F %%i in (tmpreqfile) do (
    pip install --upgrade --no-index --no-allow-external --use-wheel --find-links=%ABOUT_ROOT_DIR%\thirdparty\ -r %ABOUT_ROOT_DIR%\%%i
)
del tmpreqfile > NUL

echo.
echo * Configuring ...
:scripts
@rem Run selected configuration python scripts
%CONFIGURED_PYTHON% %ABOUT_ROOT_DIR%\etc\getconf.py --python %CMD_LINE_ARGS% > tmppyfile
for /F %%i in (tmppyfile) do (
    %CONFIGURED_PYTHON% %ABOUT_ROOT_DIR%\%%i
)
del tmppyfile > NUL


@rem Run selected configuration bat scripts
%CONFIGURED_PYTHON% %ABOUT_ROOT_DIR%\etc\getconf.py --shell %CMD_LINE_ARGS% > tmpscrfile
for /F %%i in (tmpscrfile) do (
    call %ABOUT_ROOT_DIR%\%%i
)
del tmpscrfile > NUL

@rem  enable local usage of entry points scripts
cd %ABOUT_ROOT_DIR%
pip install --upgrade --no-index --no-allow-external --find-links=%ABOUT_ROOT_DIR%\thirdparty\ --editable .


goto EOS

:clean
echo * Cleaning ...
cd %ABOUT_ROOT_DIR%
if exist %ABOUT_ROOT_DIR%\Scripts\deactivate.bat call %ABOUT_ROOT_DIR%\Scripts\deactivate
rmdir /S /Q %ABOUT_ROOT_DIR%\bin %ABOUT_ROOT_DIR%\build %ABOUT_ROOT_DIR%\Scripts %ABOUT_ROOT_DIR%\Lib %ABOUT_ROOT_DIR%\Include %ABOUT_ROOT_DIR%\build %ABOUT_ROOT_DIR%\dist 2>NUL
rmdir /S /Q %ABOUT_ROOT_DIR%\AboutCode.egg-info %ABOUT_ROOT_DIR%\eggs %ABOUT_ROOT_DIR%\parts %ABOUT_ROOT_DIR%\develop-eggs %ABOUT_ROOT_DIR%\.installed.cfg 2>NUL
goto EOS


:EOS