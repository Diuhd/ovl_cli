import argparse

import build
import init


def main():
    parser = argparse.ArgumentParser(
        prog="ovl",
        description="Make desktop overlays with modern web technology",
        epilog="Visit github for more information",
    )

    parser.add_argument(
        "action_type",
        choices=("build", "init"),
        help="Action to run",
    )

    args = parser.parse_args()

    if args.action_type == "build":
        build.main()
    else:
        init.main()


if __name__ == "__main__":
    main()
