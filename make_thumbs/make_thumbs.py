#!/usr/bin/env python3

import sys
import re
import itertools
import collections
import os
from PIL import Image
import magic
import json
import subprocess


__doc__ = """
Usage: {0} [options] [-x <path> ...] [-v ...]
       {0} --version

Options:
  -r, --root-dir=<DIR>            Directory full of images and videos
                                  to make thumbnails of.  [DEFAULT: {1}]
  -t, --thumb-root-dir=<DIR>      Directory to populate with a tree full
                                  of thumbnails.  [DEFAULT: {2}]
  -d, --dry-run                   Don't actually write any files
  -f, --force                     Overwrite existing thumbnails.
  -x, --exclude=<filename>        Directory/filename to exclude (you
                                  can list multiple by passing
                                  "-x one -x two" etc.
  -X, --excludes-file=<filename>  File with one filename/dirname
                                  per line to be excluded
  -j, --json-log=<filename>       File to output a json of original:thumbnail
                                  absolute path pairs
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

  force = args["--force"]

  verbosity = args["--verbosity"]
  v = verbosity

  json_filename = args["--json-log"]

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

  excluded_dirnames = args["--exclude"]
  excluded_filenames = args["--exclude"]
  excludes_filename = args["--excludes-file"]

  if excludes_filename is not None:
    with open(excludes_filename) as f:
      for line in f:
        line = line.rstrip()
        if os.path.isdir(line):
          excluded_dirnames.append(line)
        if os.path.isfile(line):
          excluded_filenames.append(line)
      excluded_filenames.append(excludes_filename)


  def append_to_json(pair, json_filename):
    """TODO: Partial writes so this won't disappear on Ctrl-C"""
    if os.path.isfile(json_filename):
      with open(json_filename, 'r') as f:
        current_json = json.load(f)
      current_json["pairs"].append(pair)
      with open(json_filename, 'w') as f:
        json.dump(current_json, f)
    else:
      new_json = {"pairs": [pair]}
      with open(json_filename, 'w') as f:
        json.dump(new_json, f)



  # Actually do stuff

  for (curdir, subdirs, filenames) in os.walk(image_root_dir_name,
      topdown=True):
    subdirs[:] = [
      d
      for d in subdirs
      if d not in excluded_dirnames
    ]
    for filename in filenames:
      if filename not in excluded_filenames:
        cur_path = os.path.normpath(os.path.join(curdir, filename))
        if not can_be_thumbnailed(cur_path):
          vprint(2, v, "{} not an image or video -- skipping.".format(cur_path))
          continue

        if dryrun:
          vprint(2, v, "Would deal with {} (dryrun)".format(cur_path))
        else:
          pair = deal_with(cur_path, thumb_root_dir_name, verbosity=v, size_tuple=(300, 300), force=force)
          if pair != None and json_filename != None:
            append_to_json(pair, json_filename)


def can_be_thumbnailed(path):
  return is_an_image(path) or is_a_video(path)


def is_an_image(path):
  return (magic.from_file(path, mime=True).split("/")[0] == "image")


def is_a_video(path):
  return (magic.from_file(path, mime=True).split("/")[0] == "video")


def thumb_name_from_filename(filename):
  if is_an_image(filename):
    return "t-" + os.path.basename(filename)
  elif is_a_video(filename):
    return "tv-" + os.path.basename(filename) + ".jpg"


def deal_with(filename, thumb_root_dir_name, verbosity=0, size_tuple=None, force=False):
  """
  @returns (path_of_filename, path_of_thumbnail) on success
  """
  if size_tuple == None:
    size_tuple = (120, 120)
  thumb_dir = os.path.normpath(os.path.join(thumb_root_dir_name, os.path.dirname(filename)))
  thumb_filename = os.path.join(thumb_dir, thumb_name_from_filename(filename))

  if os.path.exists(thumb_filename) and not force:
    vprint(1, verbosity, f"{thumb_filename} already exists.  If you want it clobbered, pass -f flag.")
    return None

  vprint(2, verbosity,
      f"Making thumb for\n  {filename}\nat\n  {thumb_filename}")
  try:
    os.makedirs(thumb_dir)
  except FileExistsError as e:
    pass

  try:
    create_thumbnail(filename, thumb_filename, size_tuple, verbosity)
    return (filename, thumb_filename)
  except OSError as e:
    vprint(1, verbosity, f"Error thumbnailing {filename}: {str(e)}")
    return None
  except ValueError as e:
    vprint(1, verbosity, f"I can tell {filename} is an image file, but the image library I use cannot handle it.  (Got error {str(e)})")
    return None
  except IOError as e:
    vprint(1, verbosity, f"I can tell {filename} is an image file, but the image library I use cannot handle it.  (Got error {str(e)})")
    return None


def create_thumbnail_from_image(filename, thumb_filename, size_tuple):
  im = Image.open(filename)
  im.thumbnail(size_tuple)
  im.save(thumb_filename)


def create_thumbnail_from_video(filename, thumb_filename, size_tuple, verbosity=1):
  big_thumb_filename = thumb_filename + "meta.png"
  cmdline = ["ffmpeg", "-i", filename, "-ss", "00:00:01.000", "-vframes", "1", big_thumb_filename]
  vprint(1, verbosity, "{0}".format(" ".join(cmdline)))
  subprocess.run(cmdline, check=True)
  create_thumbnail_from_image(big_thumb_filename, thumb_filename,
      size_tuple)
  vprint(1, verbosity, f"Deleting {big_thumb_filename}")
  os.remove(big_thumb_filename)


def create_thumbnail(filename, thumb_filename, size_tuple, verbosity=1):
  if is_an_image(filename):
    create_thumbnail_from_image(filename, thumb_filename, size_tuple)
  elif is_a_video(filename):
    create_thumbnail_from_video(filename, thumb_filename, size_tuple, verbosity)


if __name__ == "__main__":
  main()
