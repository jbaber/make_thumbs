from setuptools import setup

setup(
  name = "make_thumbs",
  version = "1.0.0",
  author = "John Baber-Lucero",
  author_email = "pypi@frundle.com",
  description = ("Copy a directory tree full of images to a directory tree full of thumbnails."),
  license = "GPLv3",
  url = "https://github.com/jbaber/make_thumbs",
  packages = ['make_thumbs'],
  install_requires = ['docopt', 'pillow', 'python-magic',],
  tests_require=['pytest'],
  entry_points = {
    'console_scripts': ['make-thumbs=make_thumbs.make_thumbs:main'],
  }
)
