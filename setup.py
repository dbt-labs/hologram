from setuptools import setup

requires = [
    "python-dateutil>=2.8,<2.9",
    "jsonschema<3.2,>=3.0",
    'dataclasses>=0.6,<0.9;python_version<"3.7"',
]

package_version = "0.0.13"


def read(f):
    return open(f, encoding="utf-8").read()


setup(
    name="hologram",
    description="JSON schema generation from dataclasses",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    packages=["hologram"],
    package_data={"hologram": ["py.typed"]},
    version=package_version,
    author="Connor McArthur, Jacob Beck, Simon Knibbs",
    author_email="info@fishtowanalytics.com, simon.knibbs@gmail.com",
    url="https://github.com/fishtown-analytics/hologram",
    install_requires=requires,
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries",
    ],
)
