# -*- coding: utf-8 -*-

__version__ = '1.2'

import re
import os
import subprocess
from sys import argv, stderr, exit
from datetime import datetime
from collections import OrderedDict, defaultdict
from DefaultOrderedDict import DefaultOrderedDict
from xml.dom import minidom
from optparse import OptionParser
from glob import glob
from copy import copy
from env_cabocha import envCaboCha
# import CaboCha

# for debug
import re,pprint
def pp(obj):
    pp = pprint.PrettyPrinter(indent=4, width=160)
    str = pp.pformat(obj)
    return re.sub(r"\\u([0-9a-f]{4})", lambda x: unichr(int("0x"+x.group(1),
                                                            16)), str)

class Extracted():
    def __init__(self, id):
        self.id = id
        self.last = 1
        self.current_line = 1
        self.prev_line_end = 1
        self.number = {}
        self.contents = []
        self.tags = DefaultOrderedDict(list)
        self.morph = DefaultOrderedDict(dict)

        # For debug
        self.starts = []
        self.ends  = []

    def set_contents(self, c):
        self.contents = c.split('\n')

    def set_morph(self, xml):

        def convert(node):
            """ Convert morphlogical information of SUW to dict. """

            try:
                morph = {k:v.nodeValue for k,v in dict(node.attributes).iteritems()}
                morph['word'] = node.getAttribute('originalText') or \
                                node.childNodes[0].data
                morph['start'] = int(node.getAttribute('start'))/10 - self.prev_line_end
                morph['end'] = int(node.getAttribute('end'))/10 - self.prev_line_end
                self.last = int(node.getAttribute('end'))/10
                return morph
            except: print "RERERE"  # TODO: Check the fraction SUW


        def add_line():
            """ Add buffer new line. """
            self.prev_line_end = self.last
            self.current_line += 1

        fraction_id = 0  # Used instead of start position of fraction slash
        for article in xml.getElementsByTagName('article'):
            if article.getAttribute('articleID').endswith('-Answer'):
                add_line()
            for sent in article.getElementsByTagName('sentence'):
                if sent.parentNode.tagName == 'quote' or \
                   sent.parentNode.tagName == 'quotation':
                    continue
                for luw in sent.childNodes:
                    nsib = luw.nextSibling
                    psib = luw.previousSibling

                    if luw.tagName == 'webBr':
                        if psib != None and psib.tagName != 'webBr' and nsib != None:
                            add_line()
                    elif luw.tagName != 'LUW':
                        print >>stderr, "Unknown tag name on LUW position:", luw.tagName
                    # article = luw.parentNode.parentNode.parentNode

                    for suw in luw.childNodes:
                        if suw.tagName == 'fraction':
                            skip_next = False
                            for e,s in enumerate(suw.getElementsByTagName('SUW')):
                                # Skip current node for fraction.
                                if skip_next: skip_next = False; continue
                                if s.parentNode.tagName == 'NumTrans':
                                    text = s.getAttribute('originalText')
                                    if text == '／':
                                        node = convert(s)
                                        # Reverse numerator and denominator
                                        nnode = suw.getElementsByTagName('SUW')[e+1]
                                        nnode_morph = convert(nnode)
                                        if not nnode_morph: print self.id;continue
                                        self.last = nnode_morph['end']
                                        # XXX: Can obtain correct sequence text.
                                        # 1. Previous words
                                        # 2. Numerator
                                        # 3. Fraction slash
                                        # 4. Denominator
                                        current_line_morphs = \
                                                    self.morph[self.current_line].values()
                                        fraction_prevs = dict([(i['end'],i) \
                                                            for i in current_line_morphs[:-1]])
                                        fraction_next = dict([(i['end'],i) \
                                                            for i in current_line_morphs[-1:]])

                                        # change position Numerator and Denominator

                                        # Numerator
                                        numer_key   = fraction_next.keys()[-1]
                                        numer_value = copy(nnode_morph)
                                        numer_value['start'] = fraction_next[numer_key]['start']
                                        numer_value['end'] = fraction_next[numer_key]['end']
                                        # denominator = [(next_key, next_value)]

                                        # Slash
                                        slash_position = node['end']
                                        slash_morph = node

                                        # Denominator
                                        denom_position = nnode_morph['end']
                                        denom_value    = copy(fraction_next.values()[-1])
                                        denom_value['start'] = nnode_morph['start']
                                        denom_value['end'] = nnode_morph['end']

                                        # key = self.morph[self.current_line].keys()[0]
                                        self.morph[self.current_line] = dict(
                                                fraction_prevs.items() + \
                                                {numer_key: numer_value,  # numerator
                                                 slash_position: slash_morph, # slash
                                                 denom_position: denom_value  # denominator
                                                }.items()
                                        )
                                        prev_end = nnode.getAttribute('end')
                                        skip_next = True  # Next node is already contained.
                                    else:
                                        morph = convert(s)
                                        if morph:
                                            self.morph[self.current_line][morph['end']] = morph
                                else:
                                    morph = convert(s)
                                    if morph:
                                        self.morph[self.current_line][morph['end']] = morph
                        elif suw.tagName == 'NumTrans':
                            for e,suw_in_numtrans in \
                              enumerate(suw.getElementsByTagName('SUW')):
                                morph = convert(suw_in_numtrans)
                                # Looks like sometimes morph doesn't even exist
                                # (komachi 2013-01-19)
                                if morph:
                                    self.morph[self.current_line][morph['end']] = morph
                                    self.current_last = morph['end']
                        elif suw.tagName == 'webBr':
                            add_line()
                        elif suw.tagName == 'SUW':
                            morph = convert(suw)
                            if morph:
                                self.morph[self.current_line][morph['end']] = morph
                                self.current_last = morph['end']
                        else:
                            print >>stderr, "found unknown tag name on SUW position:", suw.tagName

                    # If last element, insert newline.
                    if luw.parentNode.lastChild == luw and \
                       luw.parentNode.tagName != "quote" and \
                        (luw.parentNode.nextSibling.nextSibling == None or
                         luw.parentNode.nextSibling.nextSibling.tagName != "LUW") and \
                        (sent.getAttribute('type') != 'fragment' or \
                         sent.nextSibling.nextSibling == None):
                        add_line()
                        # Do not use ac_flag.
                        # ac_flag = "QCAnswer"

    def set_tags(self, t):
        for e,i in enumerate(t.splitlines()):
            if not i or i.startswith('np'): continue
            tag = i.strip().split('\t')
            tag_range = tag[2][1:-1].split(', ')
            tag_range = [map(int, r.split('.')) for r in tag_range]
            start = tag_range[0]
            end = tag_range[1]
            # Shifting the offset to start at 0
            start[0] -= 1
            end[0]   -= 1

            id = '.'.join([str(i) for i in end])

            # for k in [key for key, prev_range in self.tags.iteritems() \
            #           if tag_range == prev_range[2]]:
            match_key = ""
            for key, prev_ranges in self.tags.iteritems():
                for prev_range in prev_ranges:
                    if tag_range == prev_range[3]:
                        match_key = key
            if match_key:
                # If same id in self.tags
                self.tags[match_key].append([])
                info = self.tags[match_key][-1]
            else:
                # If new item
                self.tags[id] = [[]]
                info = self.tags[id][0]
            info.append(tag[0][:]) # tag name
            # info.append(tag_range) # range of tag
            word = ''
            if start[0] == end[0]: # start line number == end line number
                try:
                    word = self.contents[start[0]][start[1]:end[1]]
                except: pass
            else:
                # cannot parse a word spans more than three line
                word = ''.join([self.contents[start[0]][start[1]:],
                                self.contents[end[0]][:end[1]]])
            if not word:
                print >>stderr, "Cannot obtain word at %d.%d ~ %d.%d in %s" % \
                    (start[0], start[1], end[0], end[1], self.id)
            info.append(word)  # word
            if 'ln=' in tag[3]:
                manage = tag[3].split(';')
                # management info id(id) and reference to it(ln)
                if manage[0].startswith('id='):
                    info.append({'id':re.sub('^id=', '', manage[0]),
                                 'ln':re.sub('^ln=', '', manage[1])})
                else:
                    info.append({'id':re.sub('^id=', '', manage[1]),
                                 'ln':re.sub('^ln=', '', manage[0])})
            else:
                info.append({'id':re.sub('^id=', '', tag[3])[:-1]}) # management info id
            info.append(tag_range)
            # self.tags[info[1][0]] = info
            self.number[id] = int(re.sub('id:', '', tag[1]))

            # Error check to debug
            self.starts.append(start)
            self.ends.append(end)

    def check_morphs(self):
        for start, end in zip(self.starts, self.ends):
            try:
                self.morph[end[0]][end[1]]
            except:
                print >>stderr, "Position of the morpheme is different %s at %d.%d in %s" % \
                    (self.contents[start[0]][start[1]:end[1]], start[0], start[1], self.id)


    def get_tags(self):
        # sorting to make a sorted dictionary
        # self.tags, for example {1(end line): {2(end position): [ ..word info... ] ...} ...}
        def sorted_tags_key(dict_key):
            (line, position) = dict_key.split('.')
            position = position.zfill(4)
            return float(line+'.'+position)

        tags = DefaultOrderedDict(dict)
        for k,v in sorted(self.tags.iteritems(),
                             key=lambda t: sorted_tags_key(t[0])):
            tags[k] = v
        return tags

    def get_morph(self):
        # Sorting to make a sorted dictionary
        # self.morph, for example {1(end line): {4(end position): [ ..word info... ]}}
        sorting_dict = OrderedDict()
        for k,v in self.morph.iteritems():
            sorting_dict[k] = OrderedDict(sorted(v.iteritems(), key=lambda t2: t2[0]))
        return OrderedDict(sorted(sorting_dict.iteritems(), key=lambda t1: t1[0]))

    def get_number(self):
        return self.number

def tgr_parser(contents):
    """
    tgr ファイルをそれぞれのコンテンツに分割し、
    Extracted クラスのリストとして返す。
    """
    id_pat  = re.compile(r"^<text id=(\w+)>$")
    contains = "normal"
    formatted = []

    for line in contents.split('\n'):
        line = line.rstrip()
        m = id_pat.match(line)
        if m:
            text_id = m.group(1)
            extracted = Extracted(text_id)

        if line == "<contents>":
            contains = "contents"
            text = ""
        elif line == "</contents>":
            contains = "normal"
            extracted.set_contents(text)
        elif line == "<tags>":
            contains = "tags"
            tags = ""
        elif line == "</tags>":
            contains = "normal"
            extracted.set_tags(tags)
        elif line == "</text>":
            formatted.append(extracted)
        else:

          if contains == "contents":
              text += line + '\n'
          elif contains == "tags":
              tags += line + '\n'

    return formatted

def inputs(tgr_file, xml_folder):
    """ Return lists 'Extracted' class """

    tgrs = []
    with open(tgr_file) as tgr:
        tgr_contents = ''.join(tgr.readlines()).decode('utf-8')
        tgrs += tgr_parser(tgr_contents)

    # Set each xml to tgr
    for extracted in tgrs:
        # TODO: Join segmented sentence both files.
        # (such as ..m_1.xml, ..m_2.xml, ...)
        text_id = extracted.id
        if text_id.endswith('m_[1-9]'):
            exit(-1)
        filename = re.sub('m_0', '', text_id)
        xml = minidom.parse("%s/%s.xml" % (xml_folder, filename))
        extracted.set_morph(xml)

    return tgrs

class LineChunks:
    """ Chunks in one sentence """
    def __init__(self):
        self.chunks = OrderedDict()

    def add_chunk(self, position, chunk):
        # 0:* 1:id 2:link 3:head/func
        info = chunk.split(' ')[:4]
        info[1] = int(info[1])
        self.chunks[position] = info

    def get_chunk_from_pos(self, pos, fail=None, amb=False):
        """
        Get chunk from the chunk position
        `amb`: Get chunk from 'word' position
        """

        if not amb:
            match = self.chunks.get(pos)
            if match:
                return map(str, match)  # to join
            else:
                return fail
        else:
            chunks = self.chunks.iteritems()
            match = [(k,v) for k,v in chunks if k<=pos]
            if not match:
                return fail
            return match[-1][1]  # value


    def get_chunk_from_id(self, id, fail=None):
        # get chunk from id
        result = self.chunks.values()
        try:
            return map(str, result[id])  # to join
        except AttributeError:
            return fail

class JoinedTag:
    def __init__(self, word, morph_info):
        self.word = word
        self.morph_info = morph_info
        self.tags = defaultdict(set)

    def get_word(self):
        return self.word

    def get_tags(self):
        return dict(self.tags)

    def set_tags(self, tag):
        self.tags.update(tag)

    def get_output(self):
        if not self.word: return
        output = "%s	%s " % (self.word, self.morph_info)
        other_info = []
        for key,value in self.tags.iteritems():
            other_info.append('%s="%s"' % (key, value))
        if other_info:
            output += '/'.join(other_info)
        else:
            output += "_"
        return output

class AlreadyTags:
    """
    Already got tags before the verb word.
    It will merge JoinedTag when found verb word
    """
    def __init__(self, tags={}):
        self.tags = tags

    def get_tags(self):
        return self.tags

    def get_output(self):
        tags = []
        for key, value in self.tags.iteritems():
            tags.append('%s="%s"' % (key, value))
        return '/'.join(tags)

    def set_tags(self, tag):
        self.tags.update(tag)

class classify:
    def __init__(self, all_tags, morphs, tgr_id="UNKNOWN",
                 use_cabocha=True,
                 cabocha_option=["-I1", "-O4", "-f1", "-n1",
                                 "--posset=UNIDIC",
                                 "--charset=UTF8",
                                 "--mecabrc=./bin/mecabrc",
                                 "--rcfile=./bin/unidic_cabocharc"]):
        self.all_tags = all_tags
        self.morphs = morphs
        self.result = OrderedDict()
        self.already_ref = {}
        self.id = 1
        self.eq_id = 1
        self.bccwj_word_id = -1
        self.pword_causative_flag = False
        self.use_cabocha = use_cabocha
        self.cabocha_option = cabocha_option
        self.tgr_id = tgr_id
        if use_cabocha:
            cabocha_env = envCaboCha()
            self.cabocha_path = cabocha_env.search_cabocha()
            self.chunks = self.setup_cabocha(morphs)
            self.last_chunk_offset = [1, 0]
            self.chunk_number = 0

        d = datetime.today()
        self.day = d


    def exomap(self, position):
        if position == 11:
            return "exo1"
        elif position == 24:
            return "exo2"
        elif position == 36:
            return "exog"
        elif position == 45:
            return "exoother"

    def gaonimap(self, gaoni):
        if gaoni == u"ガ":
            return "ga"
        elif gaoni == u"ヲ":
            return "o"
        elif gaoni == u"ニ":
            return "ni"
        elif gaoni == u"ハ":
            return "ha"

    def nounmap(self, tag_type):
        if tag_type == u"内容/結果物":
            return "result"
        elif tag_type == u"役割":
            return "role"
        elif tag_type == u"モノ":
            return "object"
        elif tag_type == u"ズレ":
            return "other"

    def run_cabocha(self, inputs):
        # print >>stderr, "run cabocha:", "cabocha "+' '.join(self.cabocha_option)
        proc = subprocess.Popen([self.cabocha_path] + self.cabocha_option,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        output = proc.communicate(inputs)[0]
        if proc.returncode == 1:
            print >>stderr, "Error: CaboCha returned abnormal termination code. output: %s" % output
            exit(-1)
        return output

    def format_morph(self, morph):
        lform = morph.get("lform", '*')
        if morph.get('word') == morph.get('lemma'):
            lemma = "*"
        else:
            lemma = morph.get('lemma')
        pos = morph.get('pos', "").split('-')
        while len(pos) < 4:
            pos.append("*")
        return (lform, lemma, pos)

    def setup_cabocha(self, morphs):
        # pass to cabocha
        to_cabocha = ""
        end_line_number = morphs.keys()[-1]
        for end_line, line_morphs in morphs.iteritems():
            last_index = line_morphs.keys()[-1]
            n_line = morphs.get(end_line+1, [])
            for end_index, morph in line_morphs.iteritems():
                (lform, lemma, pos) = self.format_morph(morph)  # use only pos
                to_cabocha += "%s	%s,%s,%s,%s,*,*,*,*,*" \
                              % (morph['word'], pos[0], pos[1], pos[2], pos[3])
                if end_index == last_index:
                    # last node in current line
                    number_of_newline = 1
                    n_line_number = end_line+1
                    while not any(n_line):
                        # count following new lines in tgr
                        if n_line_number >= end_line_number:
                            break
                        n_line = morphs.get(n_line_number+1, [])
                        n_line_number += 1
                        number_of_newline += 1
                    # If next line is blank, number_of_newline is >1
                    to_cabocha += ","+"end/"*number_of_newline+"\n\n"
                else:
                    # first word in current line
                    to_cabocha += "\n"
        to_cabocha += "EOS\n"
        c_output = self.run_cabocha(to_cabocha.encode('utf-8'))

        # receive from cabocha
        c_output_iter = c_output.split('\n')
        chunks = DefaultOrderedDict(dict)
        end_line = 1
        end_index = 0
        chunks[end_line] = LineChunks()  # Initialize
        for e,line in enumerate(c_output_iter):
            if line.startswith('*'):
                chunk = line
                n_line = c_output_iter[e+1]
                n_word = n_line.split('\t')[0].decode('utf-8')
                # Necessary informations
                chunks[end_line].add_chunk(end_index+len(n_word), chunk)
            else:
                splited = line.split('\t')
                if len(splited) == 3:
                    word = splited[0].decode('utf-8')
                    word_info = splited[1]
                else:
                    continue
                # word = line.split('\t')[0].decode('utf-8')
                end_index += len(word)
                number_of_newline = word_info.count("end")
                if number_of_newline:
                    end_line += number_of_newline
                    end_index = 0
                    chunks[end_line] = LineChunks()
        return chunks


    def check_chunk_inserting(self, end_line, end_index):
        def insert_chunk(key, chunk, end_line, end_index):
            self.result[key] = ' '.join(chunk)
            self.bccwj_word_id -= 1
            self.last_chunk_offset = [end_line, end_index]

        if not self.use_cabocha:
            return
        elif self.last_chunk_offset[0] == end_line \
           and self.last_chunk_offset[1] > end_index:
            return
        elif end_line == 0:
            return

        key_0 = "%d.%d" % (end_line, end_index)
        # The key_1 is dynamic changing
        key_1 = lambda: self.bccwj_word_id
        key = lambda: (key_0, key_1())
        chunk = self.chunks[end_line].get_chunk_from_pos(end_index)
        if chunk:
            # CaboCha's chunk information starts with chunk number
            chunk_number = int(chunk[1])
            insert_chunk(key(), chunk, end_line, end_index)
        else:
            # Try to access next chunk
            # on difference position between previous chunk
            if end_line == self.last_chunk_offset[0]:
                p_end_position = self.last_chunk_offset[1]
            else:
                p_end_position = 0
                self.last_chunk_offset[0] = end_line
            diff_positions = range(p_end_position+1, end_index)
            for position in reversed(diff_positions):
                try_access = self.chunks[end_line].get_chunk_from_pos(position)
                if try_access:
                    chunk = try_access
                    chunk_number = int(chunk[1])
                    insert_chunk(key(), chunk, end_line, end_index)
                    break

    # def fix_double_word(self, word, previous_word):
    #     # If previous word is substring of current word,
    #     # remove the part of substring in current word.
    #     # For example, previous word: 保育, current word: 保育園
    #     # After current word: 園
    #     if previous_word:
    #         p_word_name = previous_word.get_word()
    #         if word and p_word_name in word and word != p_word_name:
    #             # this code has issue:
    #             # Sentence: ...|の|男の子|...
    #             # If tagged 'の' and '男の子' in tgr,
    #             # Wrong matching. prev: の this: 男の子
    #             print >>stderr, "Double words. Current word replace:", \
    #                 "prev:%s this:%s" % (p_word_name, word)
    #             word = re.sub(p_word_name, "", word)
    #     return word

    def check_alt(self, word_lemma):
        def find_pred_key(current_result, search_range=(1,3)):
            if len(current_result) < search_range[1]:
                search_range = (1, len(current_result))
            for i in range(search_range[0], search_range[1]+1):  # +1 for range function
                prev_pred_key = self.result.keys()[-i]
                prev_pred = self.result[prev_pred_key]
                if not type(prev_pred) == type(str()) and \
                "pred" in prev_pred.get_tags().get('type', ""):
                    return prev_pred_key
            else:
                # print >>stderr, "Cannot found pred for passive"
                return

        if word_lemma in (u"れる", u"られる", u"せる", u"させる"):
            if word_lemma in (u"せる", u"させる"):
                # causative
                prev_pred = find_pred_key(self.result)
                if prev_pred:
                    self.result[prev_pred].set_tags({"alt": "causative"})
                else:
                    # FIXME
                    print >>stderr, "Cannot found pred for causative"
                self.pword_causative_flag = True

            elif word_lemma in (u"れる", u"られる"):
                # passive
                if not self.pword_causative_flag:
                    prev_pred = find_pred_key(self.result)
                    if prev_pred:
                        self.result[prev_pred].set_tags({"alt": "passive"})
                    else:
                        print >>stderr, "Cannot found pred for causative"
                elif self.pword_causative_flag:
                    prev_pred = find_pred_key(self.result, search_range=(2,3))
                    if prev_pred:
                        self.result[prev_pred].set_tags({"alt": "causative/passive"})
                    else:
                        print >>stderr, "Cannot found pred for causative/passive"
                self.pword_causative_flag = False
        else:
            # If previous word was pred, it is active
            self.pword_causative_flag = False
            prev_pred = find_pred_key(self.result, search_range=(1,2))
            if prev_pred:
                # FIXME: previous was chunk case
                self.result[prev_pred].set_tags({"alt": "active"})


    def judge_zero(self, exo_flag, word_offset,
                   word_id, word_ln, line_chunks):
        # Judge reference zero(True) or dep(False)

        def get_offset_from_tags(id):
            for k,same_offset_values in self.all_tags.iteritems():
                for value in same_offset_values:
                    if value[2].get('id', "") == id:
                        return k

        if exo_flag:
            return "zero"
        if word_ln:
            ln_offset = get_offset_from_tags(word_ln)
            if not ln_offset:
                print >>stderr, "Not found link id in self.all_tags"
                return  # cannot judge
            ln_offset = tuple(map(int, ln_offset.split('.')))  # pred offset
            my_offset = word_offset                            # ga,o,ni,.. offset
            if ln_offset[0]-1 == my_offset[0]:  # If same line

                my_chunk = line_chunks.get_chunk_from_pos(my_offset[1], amb=True)
                my_id, my_link_id = (int(my_chunk[1]), int(my_chunk[2][:-1]))
                if my_link_id == '-1':  # no refer
                    return "zero"
                my_link = line_chunks.get_chunk_from_id(my_link_id)  # link info
                ln_chunk = line_chunks.get_chunk_from_pos(ln_offset[1], amb=True)
                if not ln_chunk:
                    print >>stderr, "Not found link chunk in current line"
                    return  # cannot judge
                ln_id, ln_link = (int(ln_chunk[1]), int(ln_chunk[2][:-1]))
                if ln_id == my_link_id or my_id == ln_id or ln_link == my_id:
                    return "dep"
                else:
                    return "zero"
            else:
                return "zero"

    def apply(self, word, morph,
              tag_and_link={}, end_line=None, end_index=None):

        def search_value(tuple_key_dict, id):
            # This function is for self.result
            match = [v for k,v in tuple_key_dict.iteritems() if k[1] == id]
            if match: return match[0]
            else: return None

        # tag_and_links is dict,
        # It is cannot convert to dict because it has same key in some case.
        word_tag = [k for (k,v) in tag_and_link]
        word_links = [k for (k,v) in tag_and_link]
        self.check_chunk_inserting(end_line, end_index)

        if end_line == 0:
            exo_flag = True
        else:
            exo_flag = False
        (lform, lemma, pos) = self.format_morph(morph)
        output_pos = ' '.join(pos)

        original_lemma = morph['lemma'] if morph.get('lemma') else word
        self.check_alt(original_lemma)

        if not word_links and not word_tag:
            key_0 = "%d.%d" % (end_line, end_index)
            key_1 = self.bccwj_word_id
            self.result[(key_0, key_1)] = \
                        JoinedTag(word, "%s %s %s" % (lform, lemma, output_pos))
            self.bccwj_word_id -= 1
            return

        # Does not fix double word
        # if not exo_flag:
        #     previous = self.result.values()#[-1]#.get_word()
        #     previous_word = previous[-1] if previous else ""
        #     if type(previous_word) != type(str()): # not chunk
        #         word = self.fix_double_word(word, previous_word)

        id_plus_flag = False
        eq_id_plug_flag = False
        for (tag,links) in tag_and_link:
            # self.result keys
            key_0 = "%d.%d" % (end_line, end_index)
            key_1 = links['id']
            key = (key_0, key_1)

            if tag in (u"述語", u"事態"):
                pos_type = "pred" if tag == u"述語" else "noun"
                already = self.already_ref.get(links['id'])
                if already:
                    self.result[key] = \
                                JoinedTag(word, "%s %s %s" % (lform, lemma, output_pos))
                    self.result[key].set_tags(already.get_tags())
                    self.result[key].set_tags({"type": pos_type})
                else:
                    self.result[key] = \
                                JoinedTag(word, "%s %s %s" % (lform, lemma, output_pos))
                    self.result[key].set_tags({"type": pos_type})
            elif tag in (u"ガ", u"ヲ", u"ニ", u"ハ"):
                gaoni = self.gaonimap(tag)
                if self.judge_zero(exo_flag, (end_line, end_index), links['id'],
                                   links.get('ln'), self.chunks[end_line]) == "zero":
                    gaoni_type = "zero"
                else:
                    gaoni_type = "dep"

                if search_value(self.result, links['id']) or exo_flag:
                    exo = self.exomap(end_index)
                    link = exo or str(self.id)
                    ln_match = search_value(self.result, links['ln'])
                    if ln_match:
                        ln_match.set_tags({
                            gaoni: link,
                            "%s_type" % gaoni: gaoni_type
                        })
                    else:
                        if exo_flag:
                            print >>stderr, "refer link does not exist:", links['ln']
                        else:
                            # 日本語では特殊な場合しかここに来ない
                            insert = {
                                gaoni: str(self.id),
                                "%s_type" % gaoni: gaoni_type
                            }
                            already = self.already_ref.get(links['ln'])
                            if already:
                                already.set_tags(insert)
                            else:
                                self.already_ref[links['ln']] = AlreadyTags(insert)
                else:
                    self.result[key] = \
                                JoinedTag(word, "%s %s %s" % (lform, lemma, output_pos))
                    self.result[key].set_tags({"id": str(self.id)})
                    ln_match = search_value(self.result, links['ln'])
                    if ln_match:
                        ln_match.set_tags({
                            gaoni: str(self.id),
                            "%s_type" % gaoni: gaoni_type
                        })
                    else:
                        insert = {
                            gaoni: str(self.id),
                            "%s_type" % gaoni: gaoni_type
                        }
                        already = self.already_ref.get(links['ln'])
                        if already:
                            already.set_tags(insert)
                        else:
                            self.already_ref[links['ln']] = AlreadyTags(insert)
                id_plus_flag = True
            elif tag in (u"内容/結果物", u"役割", u"モノ", u"ズレ"):
                noun_type = self.nounmap(tag)

                self.result[key] = JoinedTag(word, "%s %s %s" % (lform, lemma, output_pos))
                self.result[key].set_tags({
                    "noun_type": noun_type
                })
            elif tag == u"照応":
                if links.get('ln'):
                    ln_match = search_value(self.result, links['ln'])
                    if ln_match:
                        ln_match.set_tags({
                            "eq": str(self.eq_id),
                            "id": str(self.id)
                        })
                    if not exo_flag:
                        self.result[key] = \
                                JoinedTag(word, "%s %s %s" % (lform, lemma, output_pos))
                        self.result[key].set_tags({
                            "eq": str(self.eq_id),
                            "id": str(self.id)
                        })
                        id_plus_flag = True
                        eq_id_plug_flag = True
                else:
                    self.result[key] = \
                                JoinedTag(word, "%s %s %s" % (lform, lemma, output_pos))
            else:
                # print >>stderr, "Unknown tag in tgr:", tag
                if word and not exo_flag:
                    self.result[key] = JoinedTag(word, "%s %s %s" % (lform, lemma, output_pos))
                else:
                    print >>stderr, "Found other tag that has no word"

        if id_plus_flag:
            self.id += 1
        if eq_id_plug_flag:
            self.eq_id += 1


    def final_result(self):
        collect_tags = DefaultOrderedDict(list)
        for k,v in self.result.iteritems():
            if type(v) == type(str()):
                # chunk is controlled by self.bccwj_word_id
                collect_tags[k[1]].append(v)
            else:
                # word is controlled by its offset
                collect_tags[k[0]].append(v)
        joined_tags = OrderedDict()
        for k,v in collect_tags.iteritems():
            joined_tags[k] = v[0]
            if len(v) > 1:  # Chunk length is 1
                for v1 in v:
                    # Joining some 'JoinedTag' class
                    got_tag = v1.get_tags()
                    joined_tags[k].set_tags(got_tag)
        res = []
        str_type = type(str())
        file_head = True
        for joined in joined_tags.values():
            if type(joined) == str_type:  # chunk
                chunk = joined
                if chunk.split(' ')[1] == "0":
                    if not file_head:  # Does NOT append EOS in file head
                        res.append("EOS")
                    file_head = False
                    res.append("# S-ID:%s_%s KNP:96/10/27 %s/%s/%s" % \
                               (self.tgr_id, str(self.chunk_number).zfill(3),
                                self.day.year, self.day.month, self.day.day))
                    self.chunk_number += 1
                res.append(joined)
            else:
                if joined.get_output():  # word
                    res.append(joined.get_output())
        res.append("EOS")  # file tail
        return res

def output(tgr, tgr_id):
    """
    Return a list of the same format as the NAIST Text Corpus.
    """

    tags = tgr.get_tags()
    print >>stderr, pp(tags.values())
    morphs = tgr.get_morph()
    numbers = tgr.get_number()

    ## Join BCCWJ and tgr data

    def convert_same_offset(same_offset_tags):
        if not same_offset_tags: return
        word_tag = []
        for tag in same_offset_tags:
            # refer_tag such as ガ,オ,ニ
            (refer_tag, word_name, link, tag_range) = tag
            # word_tag[refer_tag] = link
            word_tag.append((refer_tag, link))
        return (word_name, word_tag, tag_range)


    referred_tag_number = -1
    classification = classify(tags, morphs, tgr_id, use_cabocha=True)
    for end_line, line_morphs in morphs.iteritems():
        if end_line == -1: continue  # exo will be processed after this
        for end_index, morph in line_morphs.iteritems():
            tag_positions = tags.keys()
            key = str(end_line+1) + '.' + str(end_index)
            same_offset_tag = tags.get(key, [])
            bccwj_word = morph['word']
            if same_offset_tag:
                # Tagged data matched end position in BCCWJ.
                (word_name, tag, tag_range) \
                    = convert_same_offset(same_offset_tag)
                classification.apply(bccwj_word, morph,
                                     tag, end_line, end_index)
                referred_tag_number = tag_positions.index(key)
            else:
                # To find correct end position.
                for r in range(1, len(bccwj_word)):
                    key = str(end_line+1) + '.' + str(end_index-r)
                    position = end_index-r
                    same_offset_tag = tags.get(key, [])
                    skip_flag = False
                    if same_offset_tag:
                        (word_name, tag, tag_range) \
                            = convert_same_offset(same_offset_tag)
                        if word_name in bccwj_word:
                            print >>stderr, "Treat %s in BCCWJ as %s in tgr" % \
                                (bccwj_word, word_name)
                            classification.apply(bccwj_word, morph, tag,
                                                 end_line, position)
                            referred_tag_number = tag_positions.index(key)
                            skip_flag = True
                    if skip_flag:
                        break
                else:
                    if len(tags)-1 != referred_tag_number:
                        # If not refer last tag in current line
                        n_key = tag_positions[referred_tag_number+1]
                        n_tagged_morph = tags[n_key]
                        n_word_name = n_tagged_morph[0][1]
                    else:
                        n_word_name = ""

                    # if n_word_name and bccwj_word in n_word_name:
                    #     print >>stderr, "Skipped %s in BCCWJ: %s in tgr" % \
                    #         (bccwj_word.encode('utf-8'), n_word_name.encode('utf-8'))
                    #     continue
                    # else:
                        # Cannot find same word in tgr.
                    classification.apply(bccwj_word, morph,
                                         end_line=end_line, end_index=end_index)
    # processing exo
    for offset,same_offset_tags in tags.iteritems():
        (line,position) = map(int, offset.split('.'))
        if line != 0: continue
        (word_name, word_tag, tag_range) \
            = convert_same_offset(same_offset_tags)
        for (k,v) in word_tag:  # word_tag is list (doesn't dict)
            if v['id'] == "newid0130":
                pass
        classification.apply(word_name, {}, word_tag, line, position)

    return classification.final_result()


if __name__ == '__main__':
    d = datetime.today()
    parser = OptionParser()
    parser.add_option('-t', '--tgr_dir', dest='tgr_dir',
                      default='./input/bccwj-fixed(13.03.18)/')
    parser.add_option('-b', '--bccwj_dir', dest='bccwj_dir',
                      default='./input/BCCWJ11VOL1/CORE/M-XML/')
    parser.add_option('-o', '--output_dir', dest='out_dir',
                      default='./CONVERTED/')
    parser.add_option('-d', '--debug', dest='debug_flag',
                      action='store_true', default=False)
    (opts, args) = parser.parse_args()

    if not opts.debug_flag:
        for dir in [n for n in os.listdir(opts.tgr_dir)
                    if os.path.isdir(os.path.join(opts.tgr_dir, n))]:
            try:
                os.makedirs(opts.out_dir+'/'+dir)
            except: pass
            for root, current_d, files in os.walk('%s/%s/OC/' % (opts.tgr_dir, dir)):
                for f in glob(os.path.join(root, '*.tgr')):
                    buff = ""
                    name = os.path.basename(f)
                    name = re.sub('.tgr', '.ntc', name)
                    tgrs = inputs(f, opts.bccwj_dir)
                    for tgr in tgrs:
                        tgr_id = re.sub("m_0", "", tgr.id)
                        converted = output(tgr, tgr_id)
                        buff += '\n'.join(converted) + '\n'
                    try:
                        with open('%s/%s/%s' % (opts.out_dir, dir, name), 'w') as fp:
                            fp.write(buff.encode('utf-8'))
                    except IOError, e:
                        print >>stderr, "Cannot open %s:%s" % (name, e)
                        exit(-1)
                    except UnicodeDecodeError, e:
                        print >>stderr, "Cannot decode %s:%s" % (name, e)
                        exit(-1)
    else:
        # Experiment on one file.
        # (print output to stdout and doesn't write any file)
        buff = ""
        tgrs = inputs("./input/bccwj_utf8v2(12.08.24).fixedOC.orig/B/OC/041.tgr",
                      opts.bccwj_dir)
        for tgr in tgrs:
            tgr_id = re.sub("m_0", "", tgr.id)
            converted = output(tgr, tgr_id)
            # buff += "# S-ID:%s KNP:96/10/27 %s/%s/%s\n" % \
            #         (tgr.id, d.year, d.month, d.day)
            buff += '\n'.join(converted) + '\n'
            # buff += "EOS\n"
        print buff.encode('utf-8')
