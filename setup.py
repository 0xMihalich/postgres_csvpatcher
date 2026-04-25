from setuptools import (
    Command,
    find_packages,
    setup,
)
from setuptools.command.build_py import build_py
from subprocess import check_call
from sys import executable
from pathlib import Path


class BuildLibpgQuery(Command):
    """Compiles libpg_query before installation."""

    description = "Build libpg_query native library"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        vendor_script = (
            Path(__file__).parent.absolute() /
            "vendor" / "build.py"
        )
        check_call([executable, str(vendor_script)])  # noqa: S603


class BuildPyWithNative(build_py):
    """Python build + native library."""

    def run(self):
        self.run_command("build_lib")
        super().run()


setup(
    name="postgres_csvpatcher",
    version="0.1.0",
    description = (
        "Automatically add ::timestamp(0) casts to timestamp columns in "
        "PostgreSQL CSV dump queries using native libpg_query parser"
    ),
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "postgres_csvpatcher.core": ["*.dll", "*.dylib", "*.so"],
    },
    cmdclass={
        "build_lib": BuildLibpgQuery,
        "build_py": BuildPyWithNative,
    },
    install_requires=[],
    python_requires=">=3.10",
)
