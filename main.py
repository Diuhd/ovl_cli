import argparse
from importlib import metadata
from pathlib import Path
import tomllib

import build
import init


PACKAGE_NAME = "ovllib_dev"


def get_version() -> str:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
        return project["version"]


def main():
    version = get_version()

    parser = argparse.ArgumentParser(
        prog=PACKAGE_NAME,
        description="Make desktop overlays with modern web technology",
        epilog="Visit github for more information",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PACKAGE_NAME} {version}",
    )

    parser.add_argument(
        "action_type",
        choices=("build", "init", "version"),
        help="Action to run",
    )

    args = parser.parse_args()

    if args.action_type == "build":
        build.main()
    elif args.action_type == "init":
        init.main()
    else:
        print(f"{PACKAGE_NAME} {version}")


if __name__ == "__main__":
    main()
