#!/usr/bin/env python

NUM_ROWS=144
NUM_COLS=5

key = 0
a = [ [j for j in range(NUM_COLS)] ] * NUM_ROWS
count = 0
buf = [0] * 64

for i in range(NUM_ROWS):
  for j in range(NUM_COLS): 
    if count > 0 and count % 64 == 0:
      for r in buf:
        print r
      key += 1
      buf = [0] * 64

    buf[count % 64] = "KEY_%d, a[%d][%d]" % (key, i, j)
    count += 1
