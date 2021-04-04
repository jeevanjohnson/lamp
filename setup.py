import setuptools
from config import email

with open("README.md", "r") as fh:
	long_description = fh.read()

setuptools.setup(
	name = "WebLamp",
	version = "0.2.7",
	author = "coverosu",
	author_email = email,
	description = "A socket webserver made in python!",
	long_description = long_description,
	long_description_content_type = "text/markdown",
	url = "https://github.com/coverosu/lamp",
	packages=setuptools.find_packages(),
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	python_requires='>=3.8',
)
