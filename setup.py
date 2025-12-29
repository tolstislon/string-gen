"""Setup."""

from pathlib import Path

from setuptools import find_packages, setup

README = "README.md"
readme = Path(__file__).parent / README
if not readme.exists():
    raise FileNotFoundError(f"{README} not found: {readme.absolute()}")
long_description = readme.read_bytes().decode("utf-8")

setup(
    name="string_gen",
    packages=find_packages(exclude=("tests",)),
    url="https://github.com/tolstislon/string-gen",
    license="MIT License",
    author="tolstislon",
    author_email="tolstislon@gmail.com",
    description="String generator by regex",
    long_description=long_description,
    long_description_content_type="text/markdown",
    use_scm_version={"write_to": "string_gen/__version__.py"},
    setup_requires=["setuptools_scm"],
    python_requires=">=3.8",
    include_package_data=True,
    keywords=["testing", "test-data", "test-data-generator", "string", "regex"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Testing",
    ],
)
