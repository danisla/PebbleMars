#!/usr/bin/env python

'''
PebbleMars manifest v2 generator.

Creates manifest json file with urls to bw and color images for aplite and basalt respectively.
'''
import os
import sys
import re
import json
from urllib import urlopen
import time
import datetime
import owlt
import URLtoPebblePng
import StringIO
import base64

import logging

DEFAULT_LOG_LEVEL=logging.INFO
logger = logging.getLogger(__file__)
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%dT%H:%M:%S', stream=sys.stderr, level=logging.INFO)

def timestamp():
    t = datetime.datetime.utcnow()
    ts = t.strftime("%Y-%m-%dT%H:%M:%S")
    ts += ".%03dZ" % (int(t.strftime("%f")) / 1000.0)
    return ts

def getData(model, options):

    query_base = options["API_ENDPOINT"]

    # Filter out dark images and only select color images for basalt model.
    query = query_base + "?sort=creation_timestamp_utc:desc"
    query += "&source_fields=url,color,dom_color_1,dom_color_2,dom_color_3,instrument,creation_timestamp_utc"
    query += "&q=dom_color_1:[4210752 TO 16777215] AND  dom_color_2:[4210752 TO 16777215] AND dom_color_3:[4210752 TO 16777215]"

    logger.info("Processing %s images: %s" % (model, query))

    # Fetch latest images from Image API
    if model == "aplite":
        return json.load(urlopen(query))
    elif model == "basalt":
        return json.load(urlopen(query + " AND color:true"))
    else:
        raise Exception("Unsupported model: %s" % model)


def processImage(model, img):
    '''
    Creates the following data structure:

    {
      width: 144,   # Width of the image.
      height: 168,  # Height of the image
      sol: 1004,    # Which sol the image was taken on.
      instrument: "FHAZ_LEFT_B", # Instrument the image was taken with.
      timestamp: "2015-06-03T15:13:43.001Z", # UTC time the image was acquired.
      owlt: 1272.84   # One Way Light Time (OWLT), in minutes, that it took to transmit the image.
      url: "http://mars.jpl.nasa.gov/msl-raw-images/proj/msl/redops/ods/surface/sol/01004/opgs/edr/fcam/FLB_486615455EDR_F0481570FHAZ00323M_.JPG",  # Original URL of the full res image.
      color: false, # `true` if the image is color, `false` otherwise.
      data: "<base64>" # base64 encoded PNG data.
    }
    '''

    data = {
        "width": 144,
        "height": 168
    }

    def parseSol(inst, url):
        '''Parses sol number from instrument-specific url pattern.'''

        if inst in ["mastcam_left", "mastcam_right", "mahli"]:
            sol_pat = re.compile(".*\/msss\/([0-9]+)\/")
        else:
            sol_pat = re.compile(".*\/sol\/([0-9]+)\/")

        ma = sol_pat.search(img["url"])
        if ma:
            sol_num, = ma.groups()
            return int(sol_num)
        else:
            logger.warn("Could not parse sol number from: %s" % img["url"])
            return None

    # Add sol.
    data["sol"] = parseSol(img["instrument"], img["url"])

    # Add instrument
    data["instrument"] = img["instrument"].upper()

    # Add timestamp
    data["timestamp"] = img["creation_timestamp_utc"]

    # Add owlt
    data["owlt"] = float("%.2f" % owlt.getOwlt(img["creation_timestamp_utc"]))

    # Add color
    data["color"] = img["color"]

    # Add url
    data["url"] = img["url"]

    # Add image data
    if model == "aplite":
        pebble_type = 0
    else:
        pebble_type = 1

    img_data_f = StringIO.StringIO()
    URLtoPebblePng.get_pebble_png(img["url"], pebble_type, img_data_f, True)

    img_data_f.seek(0)
    data["data"] = base64.b64encode(img_data_f.read())

    return data


def main(options):
    '''
    Create manifest with structure:

    {
      updated_at: "2015-06-18T00:00:00.000Z", # UTC timestamp of when the manifest file was last updated.
      images: [], # Array of image data (see below)
    }
    '''

    for model in ["aplite", "basalt"]:

        data = getData(model, options)

        manifest = {
            "updated_at": None,
            "images": []
        }

        # Prioritize images in the manifest by instrument.
        for i in ["fhaz", "rhaz","mastcam_left","mastcam_right","mahli","ncam"]:
            if i in data:
                for img in data[i]:
                    img_data = processImage(model, img)
                    if img_data:
                        manifest["images"].append(img_data)

        manifest["updated_at"] = timestamp()

        # Save the manifest
        f = open("manifest_%s.json" % model,'w')
        f.write(json.dumps(manifest, indent=2, separators=(',', ': ')))
        f.close()

    return


################################################################################

def parseOptions():
    options = {}

    options["MANIFEST_APLITE"] = os.environ.get("MANIFEST_APLITE", "manifest_aplite.json")
    options["MANIFEST_BASALT"] = os.environ.get("MANIFEST_BASALT", "manifest_basalt.json")

    options["API_ENDPOINT"] = os.environ.get("API_ENDPOINT", None)
    if not options["API_ENDPOINT"]:
        raise Exception("API_ENDPOINT not specified.")

    return options


if __name__ == "__main__":
    options = parseOptions()

    main(options)
