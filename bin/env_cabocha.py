#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import re
import commands

class envCaboCha:
    def on_windows(self):
        return os.name == 'nt'

    def __init__(self, cabocha_config_file):
        def cabocha_calcs():
            c = commands.getoutput("which cabocha")
            if not c:
                print >>sys.stderr, "'which cabocha' returned no string"
                exit(-1)
            return c

        if self.on_windows():
            self.cabocha_path = ["C:\Program Files\CaboCha\bin/cabocha.exe",
                                "C:\Program Files (x86)\CaboCha\bin/cabocha.exe"]
        else:
            self.cabocha_path = [cabocha_calcs()]

        self.cabocha_config = cabocha_config_file

    def search_cabocha(self):
        for c in self.cabocha_path:
            if os.path.exists(c):
                cabocha = c
                break
        else:
            print >>sys.stderr, "ERROR: Not exist cabocha at %s"\
                % (', '.join(self.cabocha_path))
            exit(-1)
        return cabocha

    def cabocha_model_dir(self, cabocha_path=""):
        if not cabocha_path:
            cabocha_path = self.search_cabocha()
        if self.on_windows():
            models = re.sub('bin/cabocha.exe$', 'model/', cabocha_path)
        else:
            models = re.sub('bin/cabocha$', 'lib/cabocha/model/', cabocha_path)
        if not os.path.exists(models):
            print >>sys.stderr, "ERROR: Not exist cabocha model directory at %s" % models
            exit(-1)
        return models

    def get_cabocha_config(self):
        return self.cabocha_config
