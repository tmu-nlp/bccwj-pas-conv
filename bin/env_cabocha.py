#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import re
import commands

class envCaboCha:
    def __init__(self):
        def cabocha_calcs():
            c = commands.getoutput("which cabocha")
            if not c:
                print >>sys.stderr, "'which cabocha' returned no string"
                exit(-1)
            return c

        self.win_cabocha = ["C:\Program Files\CaboCha\bin/cabocha.exe",
                            "C:\Program Files (x86)\CaboCha\bin/cabocha.exe"]
        self.oth_cabocha = [cabocha_calcs()]

    def on_windows(self):
        if os.name == 'nt':
            return True
        else:
            return False

    def search_cabocha(self):
        cc = self.win_cabocha if self.on_windows() else self.oth_cabocha
        for c in cc:
            if os.path.exists(c):
                cabocha = c
                break
        else:
            print >>sys.stderr, "ERROR: Not exist cabocha at %s" % (', '.join(cc))
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
