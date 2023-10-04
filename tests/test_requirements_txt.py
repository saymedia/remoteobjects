from __future__ import print_function
import os
import subprocess
import sys
import unittest


class TestRequirementsTxt(unittest.TestCase):
    def check_pip_freeze_empty(self, flags):
        # Run the pip freeze command and capture its output
        args = [sys.executable, '-m', 'pip', 'freeze', '--exclude-editable']
        args.extend(flags)
        with open(os.devnull, 'w') as fnull:
            # python 3.3: stder=subprocess.DEVNULL
            result = subprocess.check_output(args, stderr=fnull)
        lines = result.decode('utf-8').splitlines()

        # raises ValueError if not present
        added_index = lines.index(
            '## The following requirements were added by pip freeze:')
        added_dependencies = [
            line for line in lines[added_index + 1:]
            if len(line) > 0
            # workaround: as of ubuntu 20.04 (fixed in 22.04),
            # pip freeze within virtualenv gave extraneous line
            # that cannot be installed
            # https://bugs.launchpad.net/ubuntu/+source/python-pip/+bug/1635463
            and line != 'pkg-resources==0.0.0'
        ]
        if len(added_dependencies) > 0:
            self.fail(
                'Error: {} were missing recursive dependencies:\n{}'.format(
                    ' '.join(flags), '\n'.join(added_dependencies)))

    @unittest.skipUnless(
        os.environ.get('TEST_REQUIREMENTS') == 'prod',
        'requirements test must be explicitly enabled with TEST_REQUIREMENTS'
    )
    def test_requirements_txt_is_complete(self):
        '''Ensure that requirements.txt has all recursive dependencies'''
        self.check_pip_freeze_empty(['-r', 'requirements.txt'])

    @unittest.skipUnless(
        os.environ.get('TEST_REQUIREMENTS') == 'test',
        'requirements test must be explicitly enabled with TEST_REQUIREMENTS'
    )
    def test_requirements_test_txt_is_complete(self):
        '''Ensure that requirements-test.txt has all recursive dependencies'''
        self.check_pip_freeze_empty(
            ['-r', 'requirements.txt', '-r', 'requirements-test.txt'])

    def check_pip_install_empty(self, pkg, freeze_flags):
        args = [sys.executable, '-m', 'pip', 'install', '--dry-run', pkg]
        live_args = [arg for arg in args if arg != '--dry-run']
        freeze_args = [sys.executable, '-m', 'pip', 'freeze',
                       '--exclude-editable']
        freeze_args.extend(freeze_args)
        # TODO: use the --report= arg and parse json instead
        with open(os.devnull, 'w') as fnull:
            # python 3.3: stder=subprocess.DEVNULL
            result = subprocess.check_output(args, stderr=fnull)
        lines = result.decode('utf-8').splitlines()
        WOULD_INSTALL = 'Would install '
        would_install_lines = [line for line in lines
                               if line.startswith(WOULD_INSTALL)]
        self.assertGreater(
            len(would_install_lines), 0,
            'Could not find Would install line after {}'.format(
                ' '.join(args)))
        would_install_str = would_install_lines[0][len(WOULD_INSTALL):]
        would_install_packages = would_install_str.split(' ')
        would_install_packages = [
            p for p in would_install_packages
            if not p.startswith('remoteobjects-')
        ]
        self.assertEqual(
            would_install_packages, [],
            'requirements missing {}; re-run {} && {}'.format(
                ' '.join(would_install_packages),
                ' '.join(live_args),
                ' '.join(freeze_args),
            )
        )

    # skip on python2 since --dry-run was added in pip 22.2,
    # but pip stopped supporting python2 in pip 21
    # https://pip.pypa.io/en/stable/news/#v22-2
    # https://pip.pypa.io/en/stable/news/#v21-0
    @unittest.skipUnless(
        sys.version_info[0] >= 3,
        'setup.py prod requirements test requires pip 21'
    )
    def test_setup_dependencies_are_installed(self):
        '''Ensure that setup.py install_requires are all installed'''
        self.check_pip_install_empty('.', ['-r', 'requirements.txt'])

    # skip on python2 since --dry-run was added in pip 22.2,
    # but pip stopped supporting python2 in pip 21
    # https://pip.pypa.io/en/stable/news/#v22-2
    # https://pip.pypa.io/en/stable/news/#v21-0
    @unittest.skipUnless(
        sys.version_info[0] >= 3 and
        os.environ.get('TEST_REQUIREMENTS') == 'test',
        'setup.py test requirements test requires pip 21 and '
        'must be explicitly enabled with TEST_REQUIREMENTS'
    )
    def test_setup_test_dependencies_are_installed(self):
        '''Ensure that setup.py extra_require[test] are all installed'''
        self.check_pip_install_empty(
            '.[test]',
            ['-r', 'requirements.txt', '-r', 'requirements-test.txt'])
