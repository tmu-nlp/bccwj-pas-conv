#!/bin/zsh

# Convert tgr to distribute format with to_dist.py

for abcd in ../bccwj-fixed-13.03.18-4/*
do
    for field in $abcd/*
    do
        for file_name in $field/*.tgr
        do
            new_dir="dist/"${field##../bccwj-fixed-13.03.18-4/}
            mkdir -p $new_dir
            python to_dist.py $file_name > $new_dir/${file_name##*/}
            echo "wrote:"$new_dir/${file_name##*/}
        done
    done
done
