import boto
import boto.s3
from boto.s3.key import Key
import sys
import os
from os import path
import urllib
import json
import shutil

FILE_ROOT = path.join(path.dirname(__file__), 'images_processed')

BUCKET_NAME = os.environ.get("BUCKET_NAME","pebble-mars-images")

RDF_PUBLIC_URL = "https://%s.s3.amazonaws.com/update_rdf.json" % (BUCKET_NAME)
MANIFEST_PUBLIC_URL = "https://%s.s3.amazonaws.com/%s"

def main():
  conn = boto.connect_s3()
  bucket = conn.lookup(BUCKET_NAME)

  if not bucket:
    raise Exception("Could not connect to bucket: ", BUCKET_NAME)

  manifest_path = path.join(FILE_ROOT,"manifest.json")
  if not os.path.exists(manifest_path):
    print "ERROR: Manifest file not found to process"
    return

  manifest = json.loads(open(manifest_path,'r').read())
  manifest_version = manifest[0]['sol']
  manifest_version_file = "manifest_%s.json" % manifest_version
  manifest_version_path = os.path.join(os.path.dirname(manifest_path), manifest_version_file)
  shutil.copyfile(manifest_path, manifest_version_path)

  manifest_lite_path = path.join(FILE_ROOT,"manifest_lite.json")
  if os.path.exists(manifest_lite_path):
    manifest_lite_version_file = "manifest_%s_lite.json" % manifest_version
    manifest_lite_version_path = os.path.join(os.path.dirname(manifest_lite_path), manifest_lite_version_file)
    shutil.copyfile(manifest_lite_path, manifest_lite_version_path)

  def percent_cb(complete, total):
    sys.stdout.write('.')
    sys.stdout.flush()

  # Upload the manifest
  for fname in [manifest_path, manifest_version_path, manifest_lite_version_path]:
    if not os.path.exists(fname):
      print "WARN: upload src path not found: %s" % fname
      continue

    print 'Uploading %s to Amazon S3 bucket %s' % \
          (fname, BUCKET_NAME)

    k = Key(bucket)
    k.key = path.basename(fname)
    k.set_contents_from_filename(fname, cb=percent_cb, num_cb=10)
    k.make_public()
    print ""

  # Upload the RDF
  new_rdf = {
    "manifest_version": manifest[0]['sol'],
    "url": MANIFEST_PUBLIC_URL % (BUCKET_NAME, manifest_version_file),
    "ttl": 3600
  }

  fname = path.join(FILE_ROOT,"update_rdf.json")

  f = open(fname,'w')
  f.write(json.dumps(new_rdf))
  f.close()

  print 'Uploading %s to Amazon S3 bucket %s' % \
         (fname, BUCKET_NAME)

  k = Key(bucket)
  k.key = path.basename(fname)
  k.set_contents_from_filename(fname,
    cb=percent_cb, num_cb=10)

  k.make_public()
  print ""

if __name__ == '__main__':
  main()
