#!/usr/bin/bash

gource -1920x1080 -a 0.1 -s 0.075 -i 0 --logo ~/smallrotki.png --user-image-dir .git/avatar/ --background-image ~/Downloads/European_Robin_in_Dublin.jpg --highlight-users --user-scale 2.0 --max-file-lag 1 -hide filenames -o - | ffmpeg -y -r 60 -f image2pipe -vcodec ppm -i - -vcodec libx264 -preset ultrafast -pix_fmt yuv420p -crf 1 -threads 0 -bf 0 gource.mp4
