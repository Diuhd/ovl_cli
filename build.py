import subprocess
from pathlib import Path
import tomllib
import tempfile
import shutil
import threading


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

    subprocess.run(build_cmds[pkg], check=True)

    project_name = config["project"]["name"]
    frontend_output = Path(config["build"]["frontend_output"])
    build_dist = Path(config["build"]["build_dist"])
    temp_dir: Path = Path(tempfile.gettempdir()) / "ovl" / project_name

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

    archive_base = build_dist / project_name
    shutil.make_archive(
        str(archive_base),
        "zip",
        root_dir=temp_dir.parent,
        base_dir=temp_dir.name,
    )

    file_dist = build_dist / Path(f'{project_name}.zip')
    file_dist.rename(build_dist / Path(f'{project_name}.ovl'))

    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()