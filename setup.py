# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from setuptools import setup
from setuptools.command.install import install

class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        print('hello', file=open('/tmp/test','w'))


setup(
    name='brainvisa-vbox-install',
    cmdclass={
        'install': PostInstallCommand,
    },
)
