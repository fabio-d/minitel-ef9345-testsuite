from __future__ import annotations

from typing import List
import PIL.Image
import PIL.ImageSequence

from .channels import PALETTE_IMAGE, ChannelSet
from .image_utils import test_images_equal


class Screenshot:
    """
    A static or animated screenshot, in which only some channels are known.
    """

    def __init__(self, images: List[PIL.Image.Image], channels: ChannelSet):
        self.images: List[PIL.Image.Image] = []
        for image in images:
            assert image.size == images[0].size
            self.images.append(
                image.convert("RGB").quantize(
                    palette=PALETTE_IMAGE,
                    dither=PIL.Image.Dither.NONE,
                )
            )

        self.channels = channels

    def __repr__(self) -> str:
        channels = self.channels.name
        n_frames = self.n_frames
        width = self.width
        height = self.height
        return f"Screenshot({channels}#{n_frames} {width}x{height})"

    @staticmethod
    def load(path: str) -> Screenshot:
        """
        Load a still or animated screenshot from a PNG file.

        It is assumed that all the channels are valid.
        """
        images = PIL.ImageSequence.all_frames(
            PIL.Image.open(
                path,
                formats=["png"],
            )
        )
        return Screenshot(images, channels=ChannelSet.RGBI)

    @property
    def width(self) -> int:
        return self.images[0].width

    @property
    def height(self) -> int:
        return self.images[0].height

    @property
    def n_frames(self) -> int:
        return len(self.images)

    def save(self, path: str):
        converted = [img.convert("RGB") for img in self.images]
        if self.n_frames == 1:
            converted[0].save(
                path,
                format="png",
            )
        else:
            converted[0].save(
                path,
                format="png",
                append_images=converted[1:],
                duration=500,
                loop=0,
                save_all=True,
            )

    def create_matcher(self, channels: ChannelSet) -> ScreenshotMatcher:
        return ScreenshotMatcher(self.images, channels)


class _ScreenshotMatcherHelper:
    def __init__(self, images: List[PIL.Image.Image]):
        self._images = images
        self._matched_length = 0

    def advance(self, image: PIL.Image.Image) -> bool:
        # Try to advance to the next image, if it matches.
        if test_images_equal(image, self._images[self._matched_length]):
            self._matched_length += 1
            return self._matched_length == len(self._images)

        # When we have a repeated match for the same image we've already seen at
        # the previous iterations, ignore it. Otherwise, we lost the
        # synchronization and we'll have to restart from the beginning at the
        # next iteration.
        if self._matched_length != 0 and not test_images_equal(
            image, self._images[self._matched_length - 1]
        ):
            self._matched_length = 0
        return False


class ScreenshotMatcher:
    """
    Compares the given reference screenshot to a stream of images, signalling
    when a full match occurred. Only the requested channels are considered.

    If animated, the reference can have less frames than the incoming image
    stream. In this case, duplicated/redundant frames in the stream will be
    ignored. Furthermore, the stream and the reference screenshot do not need to
    start on the same frame.
    """

    def __init__(self, images: List[PIL.Image.Image], channels: ChannelSet):
        self._channels = channels

        # Instantiate an helper class instance for each possible rotation in the
        # order of the template images. Every instance will try to match a
        # specific sequence.
        images_twice = [self._channel_selector(img) for img in images] * 2
        self._helpers = [
            _ScreenshotMatcherHelper(images_twice[shift : shift + len(images)])
            for shift in range(len(images))
        ]

    def advance(self, image: PIL.Image.Image, channels: ChannelSet) -> bool:
        # All the channels that we were asked to compare must be available.
        assert (self._channels & channels) == self._channels

        # Any other channel needs to be excluded from the comparison.
        image_for_comparison = self._channel_selector(
            image.convert("RGB").quantize(
                palette=PALETTE_IMAGE,
                dither=PIL.Image.Dither.NONE,
            )
        )

        # Try to match against all the possible rotations; return success if at
        # least one signals that a full match occurred.
        for helper in self._helpers:
            if helper.advance(image_for_comparison):
                return True
        return False

    def _channel_selector(self, image: PIL.Image.Image) -> PIL.Image.Image:
        # Strip the channels that should be excluded from the comparison.
        return image.point(lambda v: v & self._channels.value, mode="P")
