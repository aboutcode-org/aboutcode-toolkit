#!/usr/bin/python

# Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.

"""
This script a configuration helper to select pip requirement files to install
and python and shell configuration scripts to execute based on provided config
directories paths arguments and the operating system platform. To use, create
a configuration directory tree that contains any of these:

 * Requirements files named with this convention:
 - base.txt contains common requirements installed on all platforms.
 - win.txt, linux.txt, mac.txt, posix.txt, cygwin.txt are platform-specific
   requirements to install.

 * Python scripts files named with this convention:
 - base.py is a common script executed on all platforms, executed before
   os-specific scripts.
 - win.py, linux.py, mac.py, posix.py, cygwin.py are platform-specific
   scripts to execute.

 * Shell or Windows CMD scripts files named with this convention:
 - win.bat is a windows bat file to execute
 - posix.sh, linux.sh, mac.sh, cygwin.sh  are platform-specific scripts to
   execute.

The config directory structure contains one or more directories paths. This
way you can have a main configuration and additional sub-configurations of a
product such as for prod, test, ci, dev, or anything else.

All scripts and requirements are optional and only used if presents. Scripts
are executed in sequence, one after the other after all requirements are
installed, so they may import from any installed requirement.

The execution order is:
 - requirements installation
 - python scripts execution
 - shell scripts execution

On posix, posix Python and shell scripts are executed before mac or linux 
scripts.

For example a tree could be looking like this::
    etc/conf
        base.txt : base pip requirements for all platforms
        linux.txt : linux-only pip requirements
        base.py : base config script for all platforms
        win.py : windows-only config script
        posix.sh: posix-only shell script

    etc/conf/prod
            base.txt : base pip requirements for all platforms
            linux.txt : linux-only pip requirements
            linux.sh : linux-only script
            base.py : base config script for all platforms
            mac.py : mac-only config script
"""

from __future__ import print_function

import os
import sys


# platform-specific file base names
sys_platform = str(sys.platform).lower()
if 'linux' in sys_platform:
    platform_names = ('posix', 'linux',)
elif'win32' in sys_platform:
    platform_names = ('win',)
elif 'darwin' in sys_platform:
    platform_names = ('posix', 'mac',)
elif 'cygwin' in sys_platform:
    platform_names = ('posix', 'cygwin',)
else:
    print('Unsupported OS/platform')
    platform_names = tuple()


# common file basenames for requirements and scripts
base = ('base',)

# known full file names with txt extension for requirements
requirements = tuple(p + '.txt' for p in base + platform_names)

# known full file names with py extensions for scripts
python_scripts = tuple(p + '.py' for p in base + platform_names)

# known full file names of shell scripts
shell_scripts = tuple(p + '.sh' for p in platform_names)
if 'win' in platform_names:
    shell_scripts = ('win.bat',)


def get_conf_files(config_dir_paths, file_names=requirements):
    """
    Based on config_dir_paths return a list of collected path-prefixed file
    paths matching names in a file_names tuple. Returned paths are posix
    paths.

    @config_dir_paths: Each config_dir_path is a relative from the project
    root to a config dir. This script should always be called from the project
    root dir.

    @file_names: get requirements, python or shell files based on list of
    supported file names provided as a tuple of supported file_names.

    Scripts or requirements are optional and only used if presents. Unknown
    scripts or requirements file_names are ignored (but they could be used
    indirectly by known requirements with -r requirements inclusion, or
    scripts with python imports.)

    Since Python scripts are executed after requirements are installed they
    can import from any requirement- installed component such as Fabric.
    """

    # collect files for each requested dir path
    collected = []

    for config_dir_path in config_dir_paths:
        # Support args like enterprise or enterprise/dev
        paths = config_dir_path.strip('/').replace('\\', '/').split('/')
        # a tuple of (relative path, location,)
        current = None
        for path in paths:
            if not current:
                current = (path, os.path.abspath(path),)
            else:
                base_path, base_loc = current
                current = (os.path.join(base_path, path),
                           os.path.join(base_loc, path),)

            path, loc = current
            # we iterate on filenames to ensure the precedence of posix over
            # mac, linux, etc is repsected
            for n in file_names:
                for f in os.listdir(loc):
                    if f == n:
                        f_loc = os.path.join(path, f)
                        if f_loc not in collected:
                            collected.append(f_loc)

    return collected


conf_types = {'--requirements': requirements,
              '--python': python_scripts,
              '--shell': shell_scripts}


if __name__ == '__main__':
    collect_what = sys.argv[1]
    if collect_what not in conf_types:
        print('First argument must be one of %s' % ', '.join(conf_types))
        sys.exit(1)

    what_to_collect = conf_types[collect_what]

    try:
        prod_confs = sys.argv[2:]
    except IndexError:
        print('Missing product/config arguments such as "etc/conf/dev".')
        sys.exit(1)

    collected = get_conf_files(prod_confs, file_names=what_to_collect)

    collected = '\n'.join(collected)

    print(collected)
