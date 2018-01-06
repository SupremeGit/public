#!/usr/bin/python
# Copyright John Sincock, 2017

# Sets the TTY width (columns).
# Setting a sufficiently large tty width will prevent wrapping/line splitting even when the output contains long package/repo names.
#
# Inspired by old plugin for yum by James Antill, at:
#   https://james.fedorapeople.org/yum/plugins/ttysz.py
#
# Test with, eg:
# dnf --width=160 list | grep python3-django-rest-framework-composed-permissions.noarch

from __future__ import print_function
import dnf.cli.term

class ttyWidth(dnf.Plugin):
    name = 'ttyWidth'

    def __init__(self, base, cli):
        super(ttyWidth, self).__init__(base, cli)
        self.base = base
        self.cli = cli

        self.cli.optparser.main_parser.add_argument('-w', '--width', dest="ttywidth", type=int, metavar='width', help="Override the tty width (use large value to prevent wrapping of output lines).")
        #print("ttyWidth: finished init.")
        
    def config(self):
        opts = self.cli.optparser.parse_command_args(self.cli.command, self.base.args)
        sz = opts.ttywidth
        if sz is not None:
            dnf.cli.term.Term.columns = sz
            print("ttyWidth: setting tty width =",sz)

        #print("Finished ttyWidth config.")
