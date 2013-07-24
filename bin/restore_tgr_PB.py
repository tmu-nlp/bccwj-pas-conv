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

def check_sampling(sentence):
    # This function returns a string that "start" or "end" or empty
    sampling = sentence.getElementsByTagName("sampling")
    if sampling:
        start_or_end = sampling[0].getAttribute("type")
        if start_or_end == "start":
            print >>sys.stderr, "Found sampling start tag"
            return "start"
        elif start_or_end == "end":
            print >>sys.stderr, "Found sampling end_tag"
            return "end"
    else:
        return ""

def extract_text(luw):
    "Extracting text from the xml node 'LUW'"

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
                        elif text.tagName == 'correction':
                            # db_value += text.childNodes[0].data
                            # try:
                            db_value += text.childNodes[0].data
                            # except AttributeError:
                            #     pass
                    except AttributeError:
                        db_value += text.data
                    except IndexError:
                        pass
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
                            elif in_suw.tagName == 'ruby':
                                db_value += in_suw.childNodes[0].data
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


def restore_tgr(dom):
    "Extracting no difference text between BCCWJ's xml and tgr"

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


def parse_bccwj(xml, tgr_id):
    # Parsing BCCWJ corpus's file

    xmldoc = minidom.parse(xml)
    id = xmldoc.getElementsByTagName('mergedSample')[0].attributes["sampleID"].value

    db_value = ""
    # TODO: Insert a newline before an answer in OC
    # for article in xmldoc.getElementsByTagName('article'):
        # if article.getAttribute('articleID').endswith('-Answer'):
        #     db_value += '\n'

    sampling_flag = False
    # sampling_start_flag = False
    sampling_end_flag = False
    if tgr_id.endswith("m_0"):
        article = xmldoc.getElementsByTagName("article")
        # if article[0].getAttribute("isWholeArticle") == "false":
        #     contents = [xmldoc]
        # else:
        contents = article
    else:
        contents = xmldoc.getElementsByTagName("div")
    for each_ad in contents:
        for sent in each_ad.getElementsByTagName('sentence'):
            if tgr_id.endswith("m_0") and sent.parentNode.tagName != "div":  # div の条件分岐はいらない?
                _sampling_flag = check_sampling(sent)
                if _sampling_flag == "start":
                    sampling_flag = True
                elif _sampling_flag == "end":
                    sampling_flag = False
                    sampling_end_flag = True

                if sampling_flag or sampling_end_flag:
                    print "sampling_flag is true, so skip the sentence"
                    sampling_end_flag = False
                    continue

            # if sent.parentNode.tagName == "quote" or \
               # sent.parentNode.parentNode.tagName == "list":
            if sent.parentNode.tagName == "quotation":
               # sent.getAttribute('type') == "verse":
                continue
            db_value += restore_tgr(sent)
    return db_value


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-t', '--tgr_dir', dest='tgr_dir', default='input/restored/')
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
                    # ex. extracted ID: OC10_00000m_0
                    raw_id = search_id.match(line.strip())
                    if raw_id:
                        # A new sentence

                        tgr_raw_id = raw_id.groups(0)[0]
                        id = tgr_raw_id[:-3]  # remove 'm_0'

                        # Open a file in BCCWJ,
                        # then check whether the file exists or not
                        xml = "%s/%s.xml" % (opts.bccwj_dir, id)
                        if not os.path.exists(xml):
                            print >>sys.stderr, "The xml doesn't exists, because you are using a release version of BCCWJ, is skipped: %s in %s" % (xml, f)
                            continue

                        sentences = parse_bccwj(xml, tgr_raw_id)
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
                        # Add the line to the now processing article
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
