# EMBedded Disk GENerator - embdgen

The embedded disk generator is a tool, that can be used, to create disk images for embedded targets.
See docs for more details.

## Requirements

Embdgen needs the following packages on ubuntu/debian:

## Required

 - `python3`
 - `python3-pip`
 - `python3-venv`
 - `libparted-dev`: Used by pyparted, to edit partition tables

```
apt install python3 python3-pip python3-venv libparted-dev
```

### Optional (required for test execution during development)
 - `mtools`:         For copying files to fat32 partitions
 - `e2fsprogs`:      For everything ext(1,2,3,4) related
 - `cryptsetup-bin`: For veritysetup, when not using the internal hash calculation algorithm
 - `dosfstools`:     For creating fat32 partitions
 - `fakeroot`:       For creating files on partitions, that usually require root (like setting uid or creating device nodes)

### For tests only
 - `fdisk`:          For verifying the partition table

```
apt install mtools e2fsprogs cryptsetup-bin fakeroot
```

## Development
It is highly recommended, to develop in a virtual environment using python 3.10:

```
python3.10 -m venv .venv
. .venv/bin/activate
```

This creates a virtual environment and activates it. If you now run `python` or `pip`, it will run in that virtual environment.

All dependencies required for development are listed in dev-requirements.txt.
They can be installed by simply running
```
pip install -r dev-requirements.txt
```

To start development in the virtual environment, install the packages in editable mode:
```
pip install -e embdgen-core
pip install -e embdgen-cominit
pip install -e embdgen-config-yaml
```
This allows having the packages installed, while still being able to edit the sources.


If installing the core package fails, because of a too old libparted, you either have to update libparted or build it manually:
```

# Make sure the venv is active
. .venv/bin/activate

# Let's do it inside the venv directory, to not pollute the source tree
cd .venv
wget https://ftpmirror.gnu.org/parted/parted-3.4.tar.xz -O - | tar -xJf -
cd parted-3.4/
./configure --prefix=$PWD/..
make -j $(nproc) install

# Now pyparted can be installed:
PKG_CONFIG_PATH=$PWD/../lib/pkgconfig/ pip install pyparted
```


### Running pylint
To run pylint for all packages, just run `scripts/run_lint.sh`

To run pylint for a single package, switch to the directory and run `pylint src`:

```
cd embdgen-core
pylint src
```

If you run pylint from the root of the repository, the correct configuration is not used and it will generate a lot of warnings

The result is printed on the command line

### Running mypy
To run mypy for all packages, just run `scripts/run_mypy.sh`

To run mypy for a single package, switch to the directory and run `mypy src`:

```
cd embdgen-core
mypy src
```

If you run mypy from the root of the repository, the correct configuration is not used and it will generate a lot of warnings

The result is printed on the command line

### Running tests
To run all tests, just run `scripts/run_tests.sh`.

To run the tests for a specific package or even a specific test in the package, switch to the directory and run `pytest`.

```
cd embdgen-core
pytest
# or
pytest tests/utils/test_SizeType.py
```

This will print the results to the console and also create a coverage report in `<package>/htmlcov`.


### Building the docs
```
cd docs
make html
```

Open it in a browser (e.g. `firefox _build/html/index.html`)
