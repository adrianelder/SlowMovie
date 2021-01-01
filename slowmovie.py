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
import os, time, sys, random
import configparser

# Ensure this is the correct import for your particular screen
from waveshare_epd import epd7in5_V2

import logging
import logging.handlers

logger = logging.getLogger('vsmp')
logger.setLevel(logging.INFO)
handler = logging.handlers.SysLogHandler(address = '/dev/log')
handler.setFormatter(logging.Formatter('[vsmp] %(message)s'))
logger.addHandler(handler)

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
VIDEO_DIR = os.path.join(BASE_DIR, 'videos')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_PATH = os.path.join(BASE_DIR, 'vsmp.conf')

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

def update(epd, globalConfig):
    rawPlaylist = globalConfig['DEFAULT'].get('playlist', '').strip().split()
    playlist = []
    # log files store the current progress for all the videos available
    for file in rawPlaylist:
        if not os.path.exists(os.path.join(VIDEO_DIR, file)):
            logger.warning('File does not exist: %s', file)
            continue
        playlist.append(file)
        try:
            log = open(progress_file_path(file))
            log.close()
        except:
            log = open(progress_file_path(file), 'w')
            log.write('0')
            log.close()
    logger.debug(playlist)

    if not playlist:
        logger.error('No playlist defined')
        exit(1)
        
    # the nowPlaying file stores the current video file
    # if it exists and has a valid video, switch to that
    try:
        f = open('nowPlaying')
        for line in f:
            currentVideo = line.strip()
        f.close()
    except:
        currentVideo = playlist[0]
        f = open('nowPlaying', 'w')
        f.write(currentVideo)
        f.close()

    if currentVideo in globalConfig:
        config = globalConfig[currentVideo]
    else:
        config = globalConfig['DEFAULT']

    logger.info('The current video is %s', currentVideo)
    frameDelay = float(config.get('frameDelay', 120))
    logger.info('Frame Delay = %f', frameDelay)
    increment = float(config.get('increment', 4))
    logger.info('Increment = %f', increment)

    currentPosition = 0

    # Open the log file and update the current position
    log = open(progress_file_path(currentVideo))
    for line in log:
        currentPosition = float(line)

    # Start frame is effectively the minimum frame index
    startFrame = int(config.get('startFrame', 0))
    if currentPosition < startFrame:
        currentPosition = startFrame
    
    inputVid = os.path.join(VIDEO_DIR, currentVideo)

    # Check how many frames are in the movie
    frameCount = int(ffmpeg.probe(inputVid)['streams'][0]['nb_frames'])

    # Convert from frame index to ms timecode assuming 24000/1001 fps.
    # TODO: Read this from video stream 'r_frame_rate' value.
    msPerFrame = 1000 / (24000 / 1001)
    msTimecode = '%dms' % (currentPosition * msPerFrame)
    # Use ffmpeg to extract a frame from the movie, crop it, letterbox it,
    # and save it as grab.jpg
    tmpFramePath = os.path.join(BASE_DIR, 'grab.jpg')
    generate_frame(
        inputVid, tmpFramePath, msTimecode, DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # Open grab.jpg in PIL
    pil_im = Image.open(tmpFramePath)
    
    brightness = float(config.get('brightness', 1))
    brightness_enhancer = ImageEnhance.Brightness(pil_im)
    pil_im = brightness_enhancer.enhance(brightness)

    contrast = float(config.get('contrast', 1))
    contrast_enhancer = ImageEnhance.Contrast(pil_im)
    pil_im = contrast_enhancer.enhance(contrast)

    # Dither the image into a 1 bit bitmap (Just zeros and ones)
    pil_im = pil_im.convert(mode='1',dither=Image.FLOYDSTEINBERG)

    # display the image
    epd.display(epd.getbuffer(pil_im))
    logger.info('Displaying frame %d of %d in %s', 
                currentPosition, frameCount, currentVideo)

    currentPosition = currentPosition + increment
    if currentPosition >= frameCount:
        currentPosition = 0
        log = open(progress_file_path(currentVideo), 'w')
        log.write(str(currentPosition))
        log.close()

        thisVideo = playlist.index(currentVideo)
        if thisVideo < len(playlist)-1:
            currentVideo = playlist[thisVideo+1]
        else:
            currentVideo = playlist[0]

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
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    return config

if __name__ == '__main__':
    main()
