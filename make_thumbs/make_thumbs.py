#!/usr/bin/env python3

import sys
import re
import itertools
import collections
import os


__doc__ = """
Usage: {0} [options] [-x <path> ...] [-v ...]
       {0} --version

Options:
  -r, --root-dir=<DIR>            Directory full of images and videos
                                  to make thumbnails of.  [DEFAULT: {1}]
  -t, --thumb-root-dir=<DIR>      Directory to populate with a tree full
                                  of thumbnails.  [DEFAULT: {2}]
  -d, --dry-run                   Don't actually write any files
  -x, --exclude=<filename>        Directory/filename to exclude (you
                                  can list multiple by passing
                                  "-x one -x two" etc.
  -X, --excludes-file=<filename>  File with one filename/dirname
                                  per line to be excluded
  -V, --version                   Show version
  -v, --verbosity                 Number of v's is level of verbosity
                                  (No -v results in silence, -vvvv is
                                  super verbose)
""".format(sys.argv[0],
        os.path.join(os.path.abspath(os.path.curdir), "images"),
        os.path.join(os.path.abspath(os.path.curdir), "thumbs"))


from docopt import docopt


def vprint(given_verbosity, verbosity, string):
  if given_verbosity <= verbosity:
    print(string)


def main():
  args = docopt(__doc__, version='1.0.0')

  dryrun = args["--dry-run"]

  verbosity = args["--verbosity"]
  v = verbosity

  image_root_dir_name = args["--root-dir"]
  if not os.path.isdir(image_root_dir_name):
    print("{} isn't a directory tree".format(image_root_dir_name))
    exit(1)

  thumb_root_dir_name = args["--thumb-root-dir"]
  if not os.path.isdir(thumb_root_dir_name):
    if dryrun:
      vprint(1, v, "Not creating {} (dryrun)".format(thumb_root_dir_name))
    else:
      vprint(1, v, "Creating {}".format(thumb_root_dir_name))
      try:
        os.makedirs(thumb_root_dir_name)
      except FileExistsError:
        pass

  excluded_dirnames = [
    os.path.abspath(d)
    for d in args["--exclude"]
    if os.path.isdir(d)
  ]
  excluded_filenames = [
    os.path.abspath(f)
    for f in args["--exclude"]
    if os.path.isfile(f)
  ]

  excludes_filename = args["--excludes-file"]
  if excludes_filename is not None:
    with open(excludes_filename) as f:
      for line in f:
        line = line.rstrip()
        if os.path.isdir(line):
          excluded_dirnames.append(os.path.abspath(line))
        if os.path.isfile(line):
          excluded_filenames.append(os.path.abspath(line))
      excluded_filenames.append(os.path.abspath(excludes_filename))

  for (curdir, subdirs, filenames) in os.walk(image_root_dir_name,
      topdown=True):
    subdirs[:] = [
      d
      for d in subdirs
      if os.path.abspath(d) not in excluded_dirnames
    ]
    for filename in filenames:
      if os.path.abspath(filename) not in excluded_filenames:
        cur_path = os.path.join(curdir, filename)
        if dryrun:
          vprint(2, v, "Would deal with {} (dryrun)".format(cur_path))
        else:
          deal_with(cur_path, thumb_root_dir_name, v)


def deal_with(filename, thumb_root_dir_name, verbosity=0):
  vprint(2, verbosity,
      f"Making thumb for {filename} in {thumb_root_dir_name}")

if __name__ == "__main__":
  main()
