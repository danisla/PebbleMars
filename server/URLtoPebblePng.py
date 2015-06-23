from PIL import Image
import urllib2
import ctypes
import argparse
import os
import png
from cStringIO import StringIO

# Create pebble 64 colors-table (r, g, b - 2 bits per channel)
def pebble_get_64color_palette():
    pebble_palette = []
    for i in xrange(0, 64):
        pebble_palette.append(((i >> 4) & 0x3) * 85)   # R
        pebble_palette.append(((i >> 2) & 0x3) * 85)   # G
        pebble_palette.append(((i     ) & 0x3) * 85)   # B
    return pebble_palette

#Get image from URL and generate pebble compliant png
def get_pebble_png(input_url, PebbleType, output_file="Pebble_image.png", zoom_fit=False):
    img = urllib2.urlopen(input_url)

    input_file = StringIO(img.read())

    #Getting current aspect ratio of image
    tempIm = Image.open(input_file)

    #first index is the width
    width = tempIm.size[0]

    #second indes is the height
    height = tempIm.size[1]

    #maintaining aspect ratio of image
    ratio = min(144/float(width),168/float(height))
    size = int(float(width*ratio)),int(float(height*ratio))

    if zoom_fit:
        im_smaller = rescale(tempIm, 144, 168)
    else:
        #resizing image to fit Pebble screen
        im_smaller = tempIm.resize(size,Image.ANTIALIAS)

    if PebbleType == 1:
        # Two step conversion process for using Pebble Time palette
        # and then dithering image

        Palet = pebble_get_64color_palette()

        paletteIm = Image.new('P',size)
        paletteIm.putpalette(Palet * 4)

        dithered_im = im_smaller.convert(mode='P',
                                         colors=64,
                                         dither=Image.FLOYDSTEINBERG,
                                         palette=Image.FLOYDSTEINBERG)

    else:
        #converting to grayscale and then dithering to black and white
        im_tempo = im_smaller.convert('LA')
        dithered_im = im_smaller.convert('1')

    #saving dithered image as PNG
    dithered_im.save(output_file,"PNG")

def rescale(img, width, height, force=True):
    """
    Rescale the given image, optionally cropping it to make sure the result image has the specified width and height.
    based on: https://djangosnippets.org/snippets/224/
    """
    max_width = width
    max_height = height

    if not force:
        img.thumbnail((max_width, max_height), Image.ANTIALIAS)
    else:
        src_width, src_height = img.size
        src_ratio = float(src_width) / float(src_height)
        dst_width, dst_height = max_width, max_height
        dst_ratio = float(dst_width) / float(dst_height)

        if dst_ratio < src_ratio:
            crop_height = src_height
            crop_width = crop_height * dst_ratio
            x_offset = int(float(src_width - crop_width) / 2)
            y_offset = 0
        else:
            crop_width = src_width
            crop_height = crop_width / dst_ratio
            x_offset = 0
            y_offset = int(float(src_height - crop_height) / 3)

        img = img.crop((x_offset, y_offset, x_offset+int(crop_width), y_offset+int(crop_height)))
        img = img.resize((dst_width, dst_height), Image.ANTIALIAS)

    return img

def main():
    parser = argparse.ArgumentParser(
        description='Get image from URL and convert to 64-color palettized PNG for Pebble Time')
    parser.add_argument('input_url', type=str,
        help='URL from which to convert image')
    parser.add_argument('PebbleType', type=int,
        help='0 is OG Pebble, 1 is Pebble Time')
    parser.add_argument('--zoom_fit', action='store_true',
        help='Zoom image to fit dimensions and preserve aspect ratio')
    parser.add_argument('--output_file', type=str, required=False,
        help='Output filename')
    args = parser.parse_args()

    if not args.output_file:
        fname,ext = os.path.splitext(os.path.basename(args.input_url))
        if args.PebbleType:
            args.output_file = "%s.color%s" % (fname, ext)
        else:
            args.output_file = "%s.grey%s" % (fname, ext)

    get_pebble_png(args.input_url, args.PebbleType, args.output_file, args.zoom_fit)


if __name__ == '__main__':
    main()
