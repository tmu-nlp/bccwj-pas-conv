#!/usr/bin/python
# encoding:utf-8
# Created on 03 July 2012 Mamoru Komachi <komachi@is.naist.jp>

import sys

def main():
  """Split a tgr file into each text"""
  import re
  id_pat  = re.compile(r"^<text id=(\w+)>$")
  contents_level = -1 # track header
  lines = []
  text_id = ""
  tgr_file = sys.argv[1]
  output_folder = sys.argv[2]
  for line in open(tgr_file, 'r'):
    lines.append(line)
    line = line.rstrip()
    #try:
    #  line = _line.rstrip().decode('utf-8')
    #except UnicodeDecodeError, e:
    #  print >>sys.stderr, "Cannot decode:%s\n" % (e)

    m = id_pat.match(line)
    if m:
      text_id = m.group(1)
    elif line == "</text>":
      write_tgr(lines, text_id, output_folder)
      lines = []
      text_id = ""

def write_tgr(lines, text_id, output_folder='./'):
  """Write lines to the file named text_id in output_folder"""
  try:
    f = open("%s/%s.tgr" % (output_folder, text_id), 'w')
    f.writelines(lines)
    f.close()
  except IOError, e:
    print >>sys.stderr, "Cannot write to %s.tgr: %s" % (e)
    sys.exit(-1)

if __name__ == "__main__":
  if len(sys.argv) != 3:
    print >>sys.stderr, "Usage: python split_tgr.py TGR_FILE OUTPUT_FOLDER"
    sys.exit(-1)
  main()
