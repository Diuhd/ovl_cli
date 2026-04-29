import subprocess
from pathlib import Path
import tomllib
import tempfile
import shutil
import threading
import re


ROOT_RELATIVE_ASSET = re.compile(
    r"(?P<attr>\b(?:href|src)=)(?P<quote>[\"'])(?P<path>/(?!/)[^\"']*)(?P=quote)"
)
FAVICON_LINK = re.compile(
    r"\s*<link\b(?=[^>]*\brel=(?P<quote>[\"'])[^\"']*\b(?:icon|shortcut icon|apple-touch-icon)\b[^\"']*(?P=quote))[^>]*>",
    re.IGNORECASE,
)


def is_favicon(filename: str):
    return filename.lower().startswith("favicon.")


def remove_favicons(frontend_output: Path):
    if not frontend_output.exists():
        return

    for path in frontend_output.rglob("*"):
        if path.is_file() and is_favicon(path.name):
            path.unlink()


def make_html_asset_paths_relative(entry_file: Path):
    if not entry_file.exists():
        return

    content = entry_file.read_text()
    content = FAVICON_LINK.sub("", content)
    content = ROOT_RELATIVE_ASSET.sub(
        lambda match: (
            f"{match.group('attr')}{match.group('quote')}"
            f".{match.group('path')}{match.group('quote')}"
        ),
        content,
    )
    entry_file.write_text(content)


def frontend_package_ignore(frontend_output: Path, build_dist: Path):
    frontend_output = frontend_output.resolve()
    build_dist = build_dist.resolve()

    try:
        build_dist_rel = build_dist.relative_to(frontend_output)
    except ValueError:
        build_dist_rel = None

    def ignore(directory, names):
        ignored = set()

        if "robots.txt" in names:
            ignored.add("robots.txt")

        ignored.update(name for name in names if is_favicon(name))

        if build_dist_rel is not None:
            current_rel = Path(directory).resolve().relative_to(frontend_output)
            if current_rel == build_dist_rel.parent and build_dist_rel.name in names:
                ignored.add(build_dist_rel.name)

        return ignored

    return ignore


def main():
    config_path = Path("ovl_config.toml")

    if not config_path.exists():
        raise SystemExit("Missing ovl.toml. Run \"ovl setup\" first.")

    config = tomllib.loads(config_path.read_text())

    pkg = config["build"]["package_manager"]

    build_cmds = {
        "npm": ["npm", "run", "build"],
        "pnpm": ["pnpm", "build"],
        "yarn": ["yarn", "build"],
        "bun": ["bun", "run", "build"],
    }

    subprocess.run(
        build_cmds[pkg],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    project_name = config["project"]["name"]
    frontend_output = Path(config["build"]["frontend_output"])
    build_dist = Path(config["build"]["build_dist"])
    temp_dir: Path = Path(tempfile.gettempdir()) / "ovl" / project_name
    remove_favicons(frontend_output)

    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    temp_dir.mkdir(parents=True, exist_ok=True)
    build_dist.mkdir(parents=True, exist_ok=True)

    threads: list[threading.Thread] = []

    config_thread = threading.Thread(
        target=lambda: shutil.copy2(
            config_path,
            temp_dir / "ovl_config.toml"
        )
    )
    web_thread = threading.Thread(
        target=lambda: shutil.copytree(
            frontend_output,
            temp_dir / config["project"]["entry_dir"],
            dirs_exist_ok=True,
            ignore=frontend_package_ignore(frontend_output, build_dist),
        )
    )
    threads.append(config_thread)
    threads.append(web_thread)

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    make_html_asset_paths_relative(
        temp_dir / config["project"]["entry_dir"] / config["project"]["entry_file"]
    )

    archive_base = build_dist / project_name
    shutil.make_archive(
        str(archive_base),
        "zip",
        root_dir=temp_dir.parent,
        base_dir=temp_dir.name,
    )

    file_dist = build_dist / Path(f'{project_name}.zip')
    output_file = build_dist / Path(f'{project_name}.ovl')
    file_dist.rename(output_file)

    print(f"{output_file.name} created in {output_file.parent}")

    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
