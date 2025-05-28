from setuptools import find_packages, setup

console_scripts = []

console_scripts.append(
    "{0}={1}.app:cli".format(
        find_packages("src")[0].replace("_", "-"), find_packages("src")[0]
    )
)

setup(
    entry_points={"console_scripts": console_scripts},
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
