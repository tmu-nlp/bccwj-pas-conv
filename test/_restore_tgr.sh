#!/bin/bash

rm -rf test/RESTORED_TGR
mkdir test/RESTORED_TGR # RAW_TGR

# for BCCWJ
python bin/restore_tgr.py -t input/bccwj_utf8v2\(12.08.24\).fixedOC.orig/ -b input/BCCWJ11VOL1/CORE/M-XML/ -o test/RESTORED_TGR;

# for tgr
for f in input/bccwj_utf8v2\(12.08.24\).fixedOC.orig/*/*/*.tgr
do
    python test/split_tgr.py $f test/RAW_TGR;
done
for f in test/RAW_TGR/*.tgr
do
    # delete m_0.tgr in file name
    python test/ext-tgr.py $f > ${f%m_[0-9].tgr}.txt;
done

rm -rf test/RAW_TGR/*.tgr
diff -ur test/RESTORED_TGR test/RAW_TGR > logs/diff
