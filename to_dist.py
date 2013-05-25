#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import re

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print >>sys.stderr, "Usage: python to_dist.py input_file"
        exit(-1)
    tgr = sys.argv[1]

    contents_flag = False
    with open(tgr) as fp:
        for line in fp:
            if line.strip() == "<contents>":
                contents_flag = True
            elif line.strip() == "</contents>":
                contents_flag = False
            elif not contents_flag:
                print line,
