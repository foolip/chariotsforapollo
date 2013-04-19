#!/bin/sh
#
# crop+resize images using ImageMagick

src="$1"
dst="$2"
maxw="$3"
maxh="$4"

identify -format "%w %h" "$src" | while read w h; do
    crop="${src%.*}.crop"
    size="${src%.*}.size"
    if [ -e "$crop" ]; then
	read top right bottom left < "$crop"
	args="-crop $(($w-$left-$right))x$(($h-$top-$bottom))+$left+$top"
    fi
    if [ -e "$size" ]; then
	read maxw maxh < "$size"
    fi
    if [ -n "$args" -o $w -gt $maxw -o $h -gt $maxh ]; then
	convert "$src" $args +repage -resize "${maxw}x${maxh}>" \
	    -strip -quality 95 "$dst"
    else
	cp "$src" "$dst"
    fi
done
