from setuptools import find_packages, setup


setup(
    name="postgres_csvpatcher",
    version="0.1.1",
    description=(
        "Automatically add ::timestamp(0) casts to timestamp columns in "
        "PostgreSQL CSV dump queries using native libpg_query parser"
    ),
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["pglast>=7.13"],
    python_requires=">=3.10",
)
