#!/usr/bin/env python3

import sys
import re
import itertools
import collections
import os
from PIL import Image
import magic
import subprocess
import hashlib


__doc__ = """
Usage: {0} [options] [-x <path> ...] [-v ...]
       {0} --version

Options:
  -r, --root-dir=<DIR>            Directory full of images and videos
                                  to make thumbnails of.  [DEFAULT: {1}]
  -t, --thumb-root-dir=<DIR>      Directory to populate with directories
                                  full of thumbnails (named for the hash
                                  of each image).  [DEFAULT: {2}]
  -d, --dry-run                   Don't actually write any files
  -f, --force                     Overwrite existing thumbnails.
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


def mkdir_exist(dirname, dryrun=False, *, verbosity=1):
  """
  Create directory named `dirname`, *not* throwing
  an exception if it already exists.
  Do nothing but make logging noise if `dryrun` is
  True
  """
  v = verbosity

  if os.path.isdir(dirname):
    vprint(1, v, "{} already exists.  Doing nothing.".format(dirname))
    return

  if os.path.exists(dirname):
    errmsg = "ERROR: {} already exists and isn't a directory".format(dirname)
    vprint(0, v, errmsg)
    raise TypeError(errmsg)

  if dryrun:
    vprint(1, v, "Not creating {} (dryrun)".format(dirname))
    return

  vprint(1, v, "Creating {}".format(dirname))
  os.makedirs(dirname)


def main():
  args = docopt(__doc__, version='2.0.0')

  dryrun = args["--dry-run"]

  force = args["--force"]

  verbosity = args["--verbosity"]
  v = verbosity

  image_root_dir_name = args["--root-dir"]
  if not os.path.isdir(image_root_dir_name):
    print("{} isn't a directory tree".format(image_root_dir_name))
    exit(1)

  thumb_root_dir_name = args["--thumb-root-dir"]
  try:
    mkdir_exist(thumb_root_dir_name)
  except TypeError as e:
    print(f"'{thumb_root_dir_name}' already exists and isn't a directory")
    exit(1)

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
          deal_with(cur_path, thumb_root_dir_name, verbosity=v, size_tuples=[(100, 100), (300, 300)],
            force=force, dryrun=dryrun)


def can_be_thumbnailed(path):
  return is_an_image(path) or is_a_video(path)


def is_an_image(path):
  return (magic.from_file(path, mime=True).split("/")[0] == "image")


def is_a_video(path):
  return (magic.from_file(path, mime=True).split("/")[0] == "video")


def thumb_names_from_filename(filename):
  return {
    "image": "t-" + os.path.basename(filename),
    "image600": "t600-" + os.path.basename(filename),
    "video": "tv-" + os.path.basename(filename) + ".jpg",
  }


def thumb_name_from_filename(filename, midsize=False):
  if is_an_image(filename):
    if midsize:
      return thumb_names_from_filename(filename)["image600"]
    return thumb_names_from_filename(filename)["image"]
  if is_a_video(filename):

    # No such thing for videos right now
    if midsize:
      return None
    return thumb_names_from_filename(filename)["video"]


def sha256sum(filename):
  h = hashlib.sha256()
  b = bytearray(128 * 1024)
  mv = memoryview(b)
  with open(filename, 'rb', buffering=0) as f:
    for n in iter(lambda: f.readinto(mv), 0):
      h.update(mv[:n])
  return h.hexdigest()


def deal_with(filename, thumb_root_dir_name, verbosity=0, size_tuples=None, force=False, dryrun=False):
  """
  @returns (path_of_filename, paths_of_thumbnails) on success
  """
  if size_tuples == None:
    size_tuples = [(120, 120)]

  # TODO Handle collisions
  hashhex = sha256sum(filename)

  thumb_dir = os.path.join(thumb_root_dir_name, hashhex)
  vprint(1, verbosity, f"Putting thumbs in {thumb_dir}")

  mkdir_exist(thumb_dir, dryrun=dryrun, verbosity=verbosity)

  for size_tuple in size_tuples:
    s_dimension = f"{size_tuple[0]}x{size_tuple[1]}"
    thumb_path = os.path.join(thumb_dir, f"{s_dimension}.jpg")
    vprint(1, verbosity, f"Creating {s_dimension} thumb at {thumb_path}")
    if os.path.exists(thumb_path) and not force:
      vprint(1, verbosity, f"{thumb_path} already exists.  If you want it "
          "clobbered, pass -f flag.")
      continue

    try:
      create_thumbnail(filename, thumb_path, size_tuple, verbosity)
    except OSError as e:
      vprint(1, verbosity, f"Error thumbnailing {filename}: {str(e)}")
      return
    except ValueError as e:
      vprint(1, verbosity, f"I can tell {filename} is an image file, but the image library I use cannot handle it.  (Got error {str(e)})")
      return
    except IOError as e:
      vprint(1, verbosity, f"I can tell {filename} is an image file, but the image library I use cannot handle it.  (Got error {str(e)})")
      return


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
