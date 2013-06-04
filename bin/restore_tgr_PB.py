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

def extract_text(luw):
    db_value = ""
    nsib = luw.nextSibling
    article = luw.parentNode.parentNode.parentNode

    for suw in luw.childNodes:
        if suw.tagName == 'fraction':
            skip_next = False
            for e,s in enumerate(suw.getElementsByTagName('SUW')):
                if skip_next: skip_next = False; continue
                if s.parentNode.tagName == 'NumTrans':
                    text = s.getAttribute('originalText')
                    if text == u'／':
                        # reverse a numerator and a denominator
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
            if len(suw.childNodes) > 1:
                for text in suw.childNodes:
                    try:
                        if text.tagName == 'sampling': pass
                        elif text.tagName == 'ruby':
                            db_value += text.childNodes[0].data
                    except AttributeError:
                        db_value += text.data
            else:
                try:
                    if suw.childNodes[0].tagName == 'enclosedCharacter':
                        # Now go in <LUW ...><SUW ...>\
                        # <enclosedCharacter description="Some character"> here </...>
                        db_value += suw.childNodes[0].childNodes[0].data
                    elif suw.childNodes[0].tagName == 'ruby':
                        db_value += suw.childNodes[0].childNodes[0].data
                except AttributeError:
                    db_value += suw.childNodes[0].data
        elif suw.tagName == 'LUW':
            # Following is used in except OC
            luw = suw
            for suw in luw.childNodes:
                if suw.tagName == 'SUW':
                    for in_suw in suw.childNodes:
                        try:
                            if in_suw.tagName == 'correction':
                                # Now go in <LUW ...><SUW ...>\
                                # <correction originalText="..." type="..."> here </...>
                                db_value += in_suw.getAttribute('originalText')
                        except AttributeError:
                            db_value += in_suw.data

                if suw.tagName == 'NumTrans':
                    db_value += suw.getAttribute('originalText')
        elif suw.tagName == 'noteMarker':
            db_value += suw.getAttribute('text')
        elif suw.tagName == 'sampling':
            pass
        else:
            print "Unknown tag name on SUW position:", suw.tagName

    return db_value


def store_db(dom):
    db_value = ""

    for luw in dom.childNodes:
        nsib = luw.nextSibling
        psib = luw.previousSibling

        if luw.tagName == 'webBr':
            if psib != None and psib.tagName != 'webBr' and nsib != None:
                db_value += "\n"
        elif luw.tagName == 'quote':
            quote = luw
            for quote_luw in quote.childNodes:
                extract_text(quote_luw)
        elif luw.tagName == 'noteMarker':
            db_value += luw.getAttribute('text')
        elif luw.tagName == 'noteBodyInline':
            db_value += luw.getAttribute('text')
        elif luw.tagName == 'sampling':
            pass
        elif luw.tagName == 'verseLine':
            print "verseLine"
        elif luw.tagName == 'image':
            print "image"
        elif luw.tagName != 'LUW':
            print "Unknown tag name on LUW position:", luw.tagName
        # article = luw.parentNode.parentNode.parentNode
        db_value += extract_text(luw)

        if db_value.endswith(u"。"):
            pass

        # If it is the last element, add newlines.

        # if luw.parentNode.parentNode.tagName == "superSentence" and \
        #    luw.parentNode.parentNode.lastChild.lastChild == luw:
        #     continue

        if luw.parentNode.lastChild == luw and \
           luw.parentNode.tagName != "quote"  and \
            (luw.parentNode.nextSibling.nextSibling == None \
             or luw.parentNode.nextSibling.nextSibling.tagName != "LUW") and \
            (dom.getAttribute('type') != 'fragment' \
             or dom.nextSibling.nextSibling == None):
            # TODO: I don't know why, but in some case,
            # do not break after the fragment.
            db_value += "\n"
        # if luw.parentNode.lastChild == luw

        if nsib == None: continue
    return db_value


def parse_bccwj(xml):
    xmldoc = minidom.parse(xml)
    id = xmldoc.getElementsByTagName('mergedSample')[0].attributes["sampleID"].value

    db_value = ""
    # TODO: Insert a newline before an answer in OC
    # for article in xmldoc.getElementsByTagName('article'):
        # if article.getAttribute('articleID').endswith('-Answer'):
        #     db_value += '\n'
    for sent in xmldoc.getElementsByTagName('sentence'):
        # if sent.parentNode.tagName == "quote" or \
           # sent.parentNode.parentNode.tagName == "list":
        if sent.parentNode.tagName == "quotation":
           # sent.getAttribute('type') == "verse":
            continue
        db_value += store_db(sent)
    return db_value


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-t', '--tgr_dir', dest='tgr_dir', default='input/bccwj-fixed(13.03.18)/')
    parser.add_option('-b', '--bccwj_dir', dest='bccwj_dir')
    parser.add_option('-o', '--output_dir', dest='out_dir')
    parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)
    (opts, args) = parser.parse_args()

    PARSING = "PB"
    header = u"【　外界(一人称)　】　　【　外界(二人称)　】　　【　外界(一般)　】　　【　節照応　】\n——————————————————————————————\n"

    if not opts.bccwj_dir or not opts.out_dir:
        print """Usage: python bin/restore_tgr.py\
             -b BCCWJ dir -o output dir -t distribution dir(option)"""
        exit(-1)

    for dir in [n for n in os.listdir(opts.tgr_dir)
                if os.path.isdir(os.path.join(opts.tgr_dir, n))]:
        # The dir is each of bccwj-fixed/*
        output_path = ('%s/%s/%s/' % (opts.out_dir, dir, PARSING))
        try:
            os.makedirs(output_path)
        except: pass

        for root, d, files in os.walk(opts.tgr_dir+'/'+dir):
            # input/bccwj-fixed/[abcde]/
            for f in glob(os.path.join("%s/%s" % (root, PARSING), '*.tgr')):
                name = os.path.basename(f)
                with open(f) as fp:
                    lines = fp.readlines()
                buf = []
                for line in lines:
                    line = line.decode('utf-8')
                    # extracted ID, example: OC10_00000m_0
                    raw_id = search_id.match(line.strip())
                    if raw_id:
                        # New sentences

                        id = raw_id.groups(0)[0][:-3]  # remove 'm_0'

                        # open BCCWJ file
                        # Confirm xml file and pass it if not exists
                        xml = "%s/%s.xml" % (opts.bccwj_dir, id)
                        if not os.path.exists(xml):
                            print >>sys.stderr, "Not exist xml, passing it: %s in %s" % (xml, f)
                            continue

                        sentences = parse_bccwj(xml)
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
                        # Add the line to now processing article
                        buf[-1].append(line)
                # tgr_file = opts.out_dir+'/'+id+'.tgr'
                try:
                    if not opts.debug:
                        with open(output_path+name, 'w') as fp:
                            for i in buf:
                                # Write each article
                                fp.write(''.join(i).encode('utf-8'))
                except IOError, e:
                    print >>sys.stderr, "Cannot open %s:%s" % (name, e)
                    sys.exit(-1)
                except UnicodeDecodeError, e:
                    print >>sys.stderr, "Cannot decode %s:%s" % (i, e)
                    sys.exit(-1)

    print "Done."
