#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import re
from copy import copy

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print >>sys.stderr, "Usage: python ext-converted.py input_file output_dir"
        exit(-1)
    ntc = sys.argv[1]
    output_dir = sys.argv[2]
    id_pat = re.compile("(?<=# S-ID:)\w+")
    result = ""
    start_flag = False
    id = ""
    with open(ntc) as fp:
        for line in fp:
            line = line.strip()
            if line.startswith("*") or line == "EOS":
                continue
            elif line.startswith("#"):
                prev_id = copy(id)
                matched = id_pat.search(line).group(0)
                id = re.sub("_[0-9]+$", "", matched)
                if start_flag and matched.endswith('000'):
                    with open("%s/%s.txt" % (output_dir, prev_id), 'w') as output:
                        output.write(result)
                    result = ""
                else:
                    start_flag = True
            else:
                word = line.split('	')[0]
                result += word
