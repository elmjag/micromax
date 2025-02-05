#!/usr/bin/env python
import time
import struct
import tarfile
from threading import Thread
from tango.server import Device, attribute

# MD3Up OAV have 7 zoom levels
NUM_ZOOM_LEVELS = 7

CORNER_SIZE = 8

# monochrome, 8-bit per pixel
IMAGE_MODE_L = 0
# rgb, 24-bit per pixel
IMAGE_MODE_RGB = 6

WIDTH = 1224
HEIGHT = 1024
HEADER_SIZE = 32

#
# number of steps between black and white we use
# for the frame corner animation
#
CORNER_GRAY_LEVELS = 5

FRAMES_ARCHIVE = "frames.tar.bz2"


def _zoom_levels():
    """
    returns an iterator over all supported zoom levels
    """
    return range(1, NUM_ZOOM_LEVELS + 1)


def _load_frames_from_archive():
    frames = {}

    with tarfile.open(FRAMES_ARCHIVE, mode="r:bz2") as tar:
        for zoom_level in _zoom_levels():
            frames[zoom_level] = tar.extractfile(f"zoom{zoom_level}").read()

    return frames


def _paint_corner(frame: bytes, color: float):
    def get_image_mode(frame: bytes):
        _, __, image_mode = struct.unpack(">IHH", frame[:8])
        return image_mode

    def get_bytes_per_pixel():
        image_mode = get_image_mode(frame)
        if image_mode == IMAGE_MODE_L:
            return 1
        if image_mode == IMAGE_MODE_RGB:
            return 3

        assert False, f"unexpected image mode {image_mode}"

    def get_line(bytes_per_pixel):
        pixels = [round(255 * color)] * (CORNER_SIZE * bytes_per_pixel)

        return bytes(pixels)

    def get_line_indices(y, bytes_per_pixel):
        start = y * WIDTH * bytes_per_pixel + HEADER_SIZE
        end = start + CORNER_SIZE * bytes_per_pixel

        return start, end

    bytes_per_pixel = get_bytes_per_pixel()
    line = get_line(bytes_per_pixel)

    data = bytearray(frame)
    for y in range(CORNER_SIZE):
        start, end = get_line_indices(y, bytes_per_pixel)
        data[start:end] = line

    return data


def _make_painted_frames(frame: bytes):
    for color in [x / (CORNER_GRAY_LEVELS - 1) for x in range(CORNER_GRAY_LEVELS)]:
        yield _paint_corner(frame, color)


def _load_images():
    images = {}
    raw_frames = _load_frames_from_archive()

    for zoom_level in _zoom_levels():
        images[zoom_level] = list(_make_painted_frames(raw_frames[zoom_level]))

    return images


class MD3(Device):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._images = _load_images()
        self._zoom_level = 1
        self._frame_number = 0

        #
        # on the real device, the frame number is incremented continuously,
        # as new frames arrive from the internal cameras
        #
        # emulate this with this dedicated frame number increment thread
        #
        Thread(target=self._increment_frame_number).start()

    def _get_image(self):
        image = self._images[self._zoom_level][self._frame_number % CORNER_GRAY_LEVELS]
        # update frame number in the header
        image[8:16] = struct.pack(">q", self._frame_number)

        return image

    def _increment_frame_number(self):
        while True:
            time.sleep(1 / 24)
            self._frame_number += 1

    @attribute(dtype="DevEncoded", format="%d")
    def video_last_image(self):
        return "VIDEO_IMAGE", self._get_image()

    @attribute(dtype="DevLong64")
    def video_last_image_counter(self):
        return self._frame_number

    @attribute(dtype="DevULong")
    def image_width(self):
        return WIDTH

    @attribute(dtype="DevULong")
    def image_height(self):
        return HEIGHT

    @attribute(dtype="DevUShort")
    def num_zoom_levels(self):
        return NUM_ZOOM_LEVELS

    #
    # video_zoom_idx attribute
    #
    video_zoom_idx = attribute(dtype="DevShort")

    @video_zoom_idx.getter
    def video_zoom_idx_read(self):
        return self._zoom_level

    @video_zoom_idx.setter
    def video_zoom_idx_write(self, val):
        self._zoom_level = val

    #
    # video_live attribute
    #
    video_live = attribute(dtype=bool)

    @video_live.getter
    def video_live_read(self):
        return True

    @video_live.setter
    def video_live_write(self, _):
        # we don't really emulate starting and stopping image stream,
        # allow client to write this attribute, but ignore the written value
        pass


if __name__ == "__main__":
    MD3.run_server()
