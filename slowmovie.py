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

from PIL import Image, ImageEnhance
import ffmpeg
import json
import os, time, sys, random

# Ensure this is the correct import for your particular screen
from waveshare_epd import epd7in5_V2

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
VIDEO_DIR = os.path.join(BASE_DIR, 'videos')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

# Ensure this matches your particular screen
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

def main():
    epd = epd7in5_V2.EPD()

    # Initialise and clear the screen
    epd.init()
    epd.Clear()

    while 1:
        config = read_config()
        update(epd, config)

    epd.sleep()
    epd7in5.epdconfig.module_exit()
    exit()



def progress_file_path(name):
    return os.path.join(LOGS_DIR, '%s<progress' % name)

def update(epd, config):
    frameDelay = float(config['frameDelay'])
    print('Frame Delay = %f' %frameDelay )

    increment = float(config['increment'])
    print('Increment = %f' %increment )

    # Scan through video folder until you find an .mp4 file
    currentVideo = ''
    videoTry = 0
    while not (currentVideo.endswith('.mp4')):
        currentVideo = os.listdir(VIDEO_DIR)[videoTry]
        videoTry = videoTry + 1

    # the nowPlaying file stores the current video file
    # if it exists and has a valid video, switch to that
    try:
        f = open('nowPlaying')
        for line in f:
            currentVideo = line.strip()
        f.close()
    except:
        f = open('nowPlaying', 'w')
        f.write(currentVideo)
        f.close()

    videoExists = 0
    for file in os.listdir(VIDEO_DIR):
        if file == currentVideo:
            videoExists = 1

    if videoExists > 0:
        print('The current video is %s' %currentVideo)
    elif videoExists == 0:
        print('error')
        currentVideo = os.listdir(VIDEO_DIR)[0]
        f = open('nowPlaying', 'w')
        f.write(currentVideo)
        f.close()
        print('The current video is %s' %currentVideo)

    movieList = []

    # log files store the current progress for all the videos available

    for file in os.listdir(VIDEO_DIR):
        if not file.startswith('.'):
            movieList.append(file)
            try:
                log = open(progress_file_path(file))
                log.close()
            except:
                log = open(progress_file_path(file), 'w')
                log.write('0')
                log.close()

    print (movieList)

    if 'file' in config:
        if config['file'] in movieList:
            currentVideo = config['file']
        else:
            print ('%s not found' % config['file'])

    print('The current video is %s' %currentVideo)

    currentPosition = 0

    # Open the log file and update the current position
    log = open(progress_file_path(currentVideo))
    for line in log:
        currentPosition = float(line)

    inputVid = os.path.join(VIDEO_DIR, currentVideo)

    # Check how many frames are in the movie
    frameCount = int(ffmpeg.probe(inputVid)['streams'][0]['nb_frames'])
    print('there are %d frames in this video' %frameCount)

    frame = currentPosition
    msTimecode = '%dms'%(frame*41.666666)
    # Use ffmpeg to extract a frame from the movie, crop it, letterbox it,
    # and save it as grab.jpg
    tmpFramePath = os.path.join(BASE_DIR, 'grab.jpg')
    generate_frame(inputVid, tmpFramePath, msTimecode, DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # Open grab.jpg in PIL
    pil_im = Image.open(tmpFramePath)
    
    if config['brightness'] is not None:
        brightness_enhancer = ImageEnhance.Brightness(pil_im)
        brightness_enhancer.enhance(config['brightness'])
    if config['contrast'] is not None:
        contrast_enhancer = ImageEnhance.Contrast(pil_im)
        contrast_enhancer.enhance(config['contrast'])

    # Dither the image into a 1 bit bitmap (Just zeros and ones)
    pil_im = pil_im.convert(mode='1',dither=Image.FLOYDSTEINBERG)

    # display the image
    epd.display(epd.getbuffer(pil_im))
    print('Displaying frame %d of %s' %(frame,currentVideo))

    currentPosition = currentPosition + increment
    if currentPosition >= frameCount:
        currentPosition = 0
        log = open(progress_file_path(currentVideo), 'w')
        log.write(str(currentPosition))
        log.close()

        thisVideo = movieList.index(currentVideo)
        if thisVideo < len(movieList)-1:
            currentVideo = movieList[thisVideo+1]
        else:
            currentVideo = movieList[0]

    log = open(progress_file_path(currentVideo), 'w')
    log.write(str(currentPosition))
    log.close()


    f = open('nowPlaying', 'w')
    f.write(currentVideo)
    f.close()

    time.sleep(frameDelay)
    epd.init()

def generate_frame(in_filename, out_filename, time, width, height):
    (
        ffmpeg
        .input(in_filename, ss=time)
        .filter('scale', width, height, force_original_aspect_ratio=1)
        .filter('pad', width, height, -1, -1)
        .output(out_filename, vframes=1)
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )

def check_mp4(value):
    if not value.endswith('.mp4'):
        raise argparse.ArgumentTypeError('%s should be an .mp4 file' % value)
    return value

def read_config():
    config = {
        'frameDelay': 120,
        'increment': 4,
        'brightness': None,
        'contrast': None,
    }
    with open(CONFIG_PATH, 'r') as f:
        config.update(json.load(f))
    return config

if __name__ == '__main__':
    main()
