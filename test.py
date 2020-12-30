#!/usr/bin/python
# -*- coding:utf-8 -*-

# *************************
# ** Before running this **
# ** code ensure you've  **
# ** turned on SPI on    **
# ** your Raspberry Pi   **
# ** & installed the     **
# ** Waveshare library   **
# *************************

import os, time, sys, random
from PIL import Image
import ffmpeg
import argparse
from pprint import pprint

def generate_frame(in_filename, out_filename, time, width, height):
    input = ffmpeg.input(in_filename, ss=time)
    input.filter('scale', width, height, force_original_aspect_ratio=1)
    input.filter('pad', width, height, -1, -1)
    (input
     .output(out_filename, vframes=1)
     .overwrite_output()
     .run(capture_stdout=True, capture_stderr=True))


def check_mp4(value):
    if not value.endswith('.mp4'):
        raise argparse.ArgumentTypeError("%s should be an .mp4 file" % value)
    return value

# Ensure this is the correct path to your video folder
viddir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Videos/')
outdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Out/')


parser = argparse.ArgumentParser(description='SlowMovie Settings')
parser.add_argument('-f', '--file', type=check_mp4,
    help="Add a filename to start playing a specific film. Otherwise will pick a random file, and will move to another film randomly afterwards.")
parser.add_argument('-c', '--count',  type=int, default=10,
    help="The number of frames to extract")
parser.add_argument('-p', '--probe',  type=bool, default=False,
    help="Display probe metatdata and exit")

args = parser.parse_args()

print('Try to start playing %s' %args.file)
currentVideo = args.file

# Ensure this matches your particular screen
width = 800
height = 480

inputVid = os.path.join(viddir, currentVideo)

# Check how many frames are in the movie
metadata = ffmpeg.probe(inputVid)
if args.probe:
    pprint(metadata)
    exit()
frameCount = int(metadata['streams'][0]['nb_frames'])
print("there are %d frames in this video" %frameCount)

for i, frame in enumerate(range(0, frameCount, frameCount // args.count)):
    msTimecode = "%dms"%(frame*41.666666)
    # Use ffmpeg to extract a frame from the movie, crop it, letterbox it and save it as grab.jpg

    generate_frame(inputVid, 'grab.jpg', msTimecode, width, height)
    # Open grab.jpg in PIL
    pil_im = Image.open("grab.jpg")

    # Dither the image into a 1 bit bitmap
    pil_im = pil_im.convert(mode='1', dither=Image.FLOYDSTEINBERG)

    # display the image
    testFrameName = '%s-%d.jpg' % (currentVideo[:-4], i)
    print('Saving frame %d  to %s' %(frame, testFrameName))
    pil_im.save(os.path.join(outdir, testFrameName), 'JPEG')
