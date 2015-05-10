SRC=$1
DEST="${SRC}.pbl.png"

convert $SRC \
   -adaptive-resize '144x168>'\
   -fill '#FFFFFF00'\
   -opaque none\
   -dither FloydSteinberg\
   -remap pebble_colors_64.gif\
   -define png:compression-level=9\
   -define png:compression-strategy=0\
   -define png:exclude-chunk=all\
   $DEST
