#!/usr/bin/env python3

import sys
import re
import itertools
import collections
import os

__doc__ = """
Usage: {0} [options]
       {0} --version

Options:
  -r, --root-dir=<DIR>       Directory full of images and videos
                             to make thumbnails of.  [DEFAULT: {1}]
  -t, --thumb-root-dir=<DIR> Directory to populate with a tree full
                             of thumbnails.  [DEFAULT: {2}]
  -v, --version              Show version
""".format(sys.argv[0],
        os.path.join(os.path.abspath(os.path.curdir), "images"),
        os.path.join(os.path.abspath(os.path.curdir), "thumbs"))


from docopt import docopt


def main():
  args = docopt(__doc__, version='1.0.0')

  image_root_dir_name = args["--root-dir"]
  if not os.path.isdir(image_root_dir_name):
    print("{} isn't a directory tree".format(image_root_dir_name))
    exit(1)
  for (root, dirs, files) in os.walk(image_root_dir_name):
    print(root, dirs, files)


if __name__ == "__main__":
  main()
