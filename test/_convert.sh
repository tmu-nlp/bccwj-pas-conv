#!/bin/bash

mkdir -p test/RAW_TGR_ONELINE

# Usage: test/_convert.sh && diff -ur test/RAW_TGR_ONELINE test/EXTED_CONVERTED

# for tgr
for f in input/bccwj_utf8v2\(12.08.24\).fixedOC.orig/*/*/*.tgr
do
    python test/split_tgr.py $f test/RAW_TGR_ONELINE;
done
for f in test/RAW_TGR_ONELINE/*.tgr
do
    # delete m_0.tgr in file name
    txt_name=${f%m_[0-9].tgr}.txt;
    python test/ext-tgr.py $f > $txt_name'.orig';
    tr -d '\n' < $txt_name'.orig' > $txt_name;
done
rm -f test/RAW_TGR_ONELINE/*.orig

mkdir -p test/EXTED_CONVERTED

for f in CONVERTED/*/*.ntc
do
    # txt_name=${f%.ntc}.txt;
    # output_name=${txt_name#CONVERTED/*/};
    python test/ext-converted.py $f test/EXTED_CONVERTED;
done

rm -rf test/RAW_TGR_ONELINE/*.tgr
