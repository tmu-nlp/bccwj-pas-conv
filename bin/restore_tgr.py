#!/usr/bin/python
#coding: utf-8

import sys
import re
import os
from glob import glob
from xml.dom import minidom
from optparse import OptionParser

search_id = re.compile('^<text id=(\w+)>$')
search_name = re.compile('.*/(.+)')

def store_db(dom):
    db_value = ""
    ac_flag = 'QCQuestion'

    for luw in dom.getElementsByTagName('LUW'):
        nsib = luw.nextSibling
        psib = luw.previousSibling

        #if luw.tagName == 'webBr':
        #    if psib != None and psib.tagName != 'webBr' and nsib != None:
        #        db_value += "\n"
        #elif luw.tagName != 'LUW':
        #    print "Unknown tag name on LUW position:", luw.tagName
        if psib != None and psib.tagName == 'webBr':
            db_value += "\n"
        article = luw.parentNode.parentNode.parentNode

        for suw in luw.childNodes:
            if suw.tagName == 'fraction':
                skip_next = False
                for e,s in enumerate(suw.getElementsByTagName('SUW')):
                    if skip_next: skip_next = False; continue
                    if s.parentNode.tagName == 'NumTrans':
                        text = s.getAttribute('originalText')
                        if text == u'／':
                            # reverse numerator and denominator
                            nnode = suw.getElementsByTagName('SUW')[e+1]
                            nnode_text = nnode.getAttribute('originalText') or \
                                         nnode.childNodes[0].data
                            db_value = db_value[:-1] + \
                                       nnode_text + u'／' + db_value[-1:]
                            skip_next = True
                        else:
                            db_value += text
                    else:
                        db_value += s.childNodes[0].data
            elif suw.tagName == 'NumTrans':
                db_value += suw.getAttribute('originalText')
            elif suw.tagName == 'webBr':
                db_value += '\n'
            elif suw.tagName == 'SUW':
                if suw.childNodes[0].nodeType == suw.TEXT_NODE:
                    db_value += suw.childNodes[0].data
            else:
                print "Unknow tag name on SUW position:", suw.tagName

        # If it is the last element, add a newline.
        if luw.parentNode.lastChild == luw and \
           luw.parentNode.tagName != "quote" and \
            (luw.parentNode.nextSibling.nextSibling == None or
             luw.parentNode.nextSibling.nextSibling.tagName != "LUW") and \
            (dom.getAttribute('type') != 'fragment' or \
             dom.nextSibling.nextSibling == None):
            db_value += "\n"
            ac_flag = "QCAnswer"

        if nsib == None: continue
    return db_value


def parse_bccwj(xml):
    xmldoc = minidom.parse(xml)
    id = xmldoc.getElementsByTagName('mergedSample')[0].attributes["sampleID"].value
    # print id
    db_key = "%s" % (id)

    db_value = ""
    for article in xmldoc.getElementsByTagName('article'):
        if article.getAttribute('articleID').endswith('-Answer'):
            db_value += '\n'
        for sent in article.getElementsByTagName('sentence'):
            #if sent.parentNode.tagName == "quote" or \
            #   sent.parentNode.tagName == "quotation":
            #    continue
            db_value += store_db(sent)
    return db_value


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-t', '--tgr_dir', dest='tgr_dir', default="input/dist/")
    parser.add_option('-b', '--bccwj_dir', dest='bccwj_dir')
    parser.add_option('-o', '--output_dir', dest='out_dir')
    parser.add_option('-d', '--debug', dest='debug', default=False)
    parser.add_option('-g', '--genre', dest='genre', default='OC')
    (opts, args) = parser.parse_args()

    PARSING = opts.genre

    if not opts.bccwj_dir or not opts.out_dir:
        print """Usage: python bin/restore_tgr.py\
             -b BCCWJ dir -o output dir -t distribution dir(option)"""
        exit(-1)

    try:
        os.makedirs(opts.out_dir)
    except: pass

    header = u"【　外界(一人称)　】　　【　外界(二人称)　】　　【　外界(一般)　】　　【　節照応　】\n——————————————————————————————\n"

    for dir in [n for n in os.listdir(opts.tgr_dir)
                if os.path.isdir(os.path.join(opts.tgr_dir, n))]:
        try:
            os.makedirs("%s/%s/%s" % (opts.out_dir, dir, PARSING))
        except: pass

        # The dir is each of bccwj-fixed/*
        for root, d, files in os.walk(opts.tgr_dir+'/'+dir):
            # root is input/bccwj-fixed/[abcde]/
            for f in glob(os.path.join("%s/%s" % (root, PARSING), '*.tgr')):
                name = os.path.basename(f)
                with open(f) as fp:
                    lines = fp.readlines()
                buf = []
                for line in lines:
                    line = line.decode('utf-8')
                    raw_id = search_id.match(line.strip())
                    if raw_id:
                        # New sentences

                        id = raw_id.groups(0)[0][:-3]  # remove 'm_0'

                        # open BCCWJ file
                        sentences = parse_bccwj("%s/%s.xml" % (opts.bccwj_dir, id))
                        contents = []
                        if opts.debug:
                            print "%s/%s.txt" % (opts.out_dir, id)
                            with open('%s/%s.txt' % (opts.out_dir, id), 'w') as fp:
                                fp.write(sentences)
                        contents.append(line)
                        contents.append('<contents>\n')
                        contents.append(header)
                        contents.append(sentences)
                        contents.append('</contents>\n')
                        buf.append(contents)
                    else:
                        # Add one line to recognized sentences
                        buf[-1].append(line)
                # tgr_file = opts.out_dir+'/'+id+'.tgr'
                try:
                    if not opts.debug:
                        with open('%s/%s/%s/%s' % (opts.out_dir, dir, PARSING, name), 'w') as fp:
                            for i in buf:
                                fp.write(''.join(i).encode('utf-8'))
                except IOError, e:
                    print >>sys.stderr, "Cannot open %s:%s" % (name, e)
                    sys.exit(-1)
                except UnicodeDecodeError, e:
                    print >>sys.stderr, "Cannot decode %s:%s" % (i, e)
                    sys.exit(-1)

    print "Done."
