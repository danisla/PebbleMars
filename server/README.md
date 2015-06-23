# PebbleMars Server

The server-side component to PebbleMars that generates the manifest used by the watchapp.

The app fetches the manifest and uses the S3 caching mechanism to know when to refresh.  This lets the user see the stream of latest images without making constant HTTP queries and allows the watchface to work even when there is no cellular or wifi coverage.

## manifest_aplite.json

Contains the image manifest for the original Pebble and Pebble Steel models.

The most recent 10 images are converted to dithered greyscale PNGs and encoded as base64 into JSON fields.

## manifest_basalt.json

Contains the image manifest for the Pebble Time and Pebble Time Steel models.

The most recent 10 _color_ images are converted to the 64 color dithered PNG format and encoded to base64.

Color images are chosen using the instrument it was taken by and using the Python Image module to detect "interesting" images. Interesting images are those that are mostly color (no black images). The Rovers periodically take negative images or images of the sun on Mars for navigation and calibration purposes, these don't look very good on the Pebble so they are filtered out.

An option will be available in the configure screen for the watchapp to choose wether or not to show only color images or to also include the greyscale images as they are more frequent and often contain interesting features.

# JSON Manifest Structure

The manifest includes information about each image that will be used by the watchface.

Manifest structure:

```
{
  updated_at: "2015-06-18T00:00:00.000Z", # UTC timestamp of when the manifest file was last updated.
  images: [], # Array of image data (see below)
}
```

`images` structure:

```
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
```
