from InquirerPy.resolver import prompt
from InquirerPy.exceptions import InvalidArgument
from InquirerPy.validator import EmptyInputValidator
import subprocess
from pathlib import Path

from tomlkit import comment, document, nl, table
from tomlkit.toml_file import TOMLFile

def run_quiet(cmd: list[str], cwd: str | None = None):
    subprocess.run(
        cmd,
        check=True,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def install_dev_dependency(pkg_manager: str, package: str, cwd: str):
    if pkg_manager == "npm":
        cmd = ["npm", "install", "-D", package]
    elif pkg_manager == "pnpm":
        cmd = ["pnpm", "add", "-D", package]
    elif pkg_manager == "yarn":
        cmd = ["yarn", "add", "-D", package]
    elif pkg_manager == "bun":
        cmd = ["bun", "add", "-d", package]
    else:
        raise ValueError("Unsupported package manager")

    run_quiet(cmd, cwd=cwd)


def update_client_build_config_for_static_output(project_dir: str):
    for config_name in ("vite.config.ts", "vite.config.js", "vite.config.mts", "vite.config.mjs"):
        config_path = Path(project_dir) / config_name
        if not config_path.exists():
            continue

        content = config_path.read_text()

        if "outDir:" in content:
            content = content.replace("outDir: 'dist'", "outDir: 'build'")
            content = content.replace('outDir: "dist"', 'outDir: "build"')
        elif "plugins:" in content:
            content = content.replace(
                "plugins: [",
                "build: {\n    outDir: 'build',\n  },\n  plugins: [",
                1,
            )
        else:
            content = content.replace(
                "export default defineConfig({\n",
                "export default defineConfig({\n  build: {\n    outDir: 'build',\n  },\n",
                1,
            )

        if "base:" not in content:
            content = content.replace(
                "export default defineConfig({\n",
                "export default defineConfig({\n  base: './',\n",
                1,
            )

        config_path.write_text(content)
        return

    raise FileNotFoundError("Unable to find a client build config file to update")


def ensure_sveltekit_prerendered(language: str, project_dir: str):
    extension = "ts" if language == "TypeScript" else "js"
    layout_path = Path(project_dir) / "src" / "routes" / f"+layout.{extension}"
    layout_path.write_text("export const prerender = true;\n")


def update_sveltekit_for_static_output(
    pkg_manager: str, language: str, project_dir: str
):
    install_dev_dependency(pkg_manager, "@sveltejs/adapter-static", project_dir)

    for config_name in ("svelte.config.js", "svelte.config.ts"):
        config_path = Path(project_dir) / config_name
        if not config_path.exists():
            continue

        content = config_path.read_text()
        content = content.replace("@sveltejs/adapter-auto", "@sveltejs/adapter-static")
        content = content.replace(
            "adapter: adapter()",
            "adapter: adapter({\n      pages: 'build',\n      assets: 'build'\n    })",
        )
        config_path.write_text(content)
        ensure_sveltekit_prerendered(language, project_dir)
        return

    raise FileNotFoundError("Unable to find a SvelteKit config file to update")


def create_project(pkg_manager: str, framework: str, language: str, name: str):
    if framework == "sveltekit":
        types = "ts" if language == "TypeScript" else "jsdoc"

        if pkg_manager == "npm":
            cmd = [
                "npx",
                "--yes",
                "sv",
                "create",
                name,
                "--template",
                "minimal",
                "--types",
                types,
                "--no-add-ons",
                "--install",
                pkg_manager,
                "--no-dir-check",
            ]
        elif pkg_manager == "pnpm":
            cmd = [
                "pnpm",
                "dlx",
                "sv",
                "create",
                name,
                "--template",
                "minimal",
                "--types",
                types,
                "--no-add-ons",
                "--install",
                pkg_manager,
                "--no-dir-check",
            ]
        elif pkg_manager == "yarn":
            cmd = [
                "yarn",
                "dlx",
                "sv",
                "create",
                name,
                "--template",
                "minimal",
                "--types",
                types,
                "--no-add-ons",
                "--install",
                pkg_manager,
                "--no-dir-check",
            ]
        elif pkg_manager == "bun":
            cmd = [
                "bunx",
                "sv",
                "create",
                name,
                "--template",
                "minimal",
                "--types",
                types,
                "--no-add-ons",
                "--install",
                pkg_manager,
                "--no-dir-check",
            ]
        else:
            raise ValueError("Unsupported package manager")

        run_quiet(cmd)
        update_sveltekit_for_static_output(pkg_manager, language, name)
        return

    templates = {
        "react": {
            "TypeScript": "react-ts",
            "JavaScript": "react",
        },
        "vue": {
            "TypeScript": "vue-ts",
            "JavaScript": "vue",
        },
        "solid": {
            "TypeScript": "solid-ts",
            "JavaScript": "solid",
        },
        "vanilla": {
            "TypeScript": "vanilla-ts",
            "JavaScript": "vanilla",
        },
    }

    template = templates[framework][language]

    if pkg_manager == "npm":
        cmd = [
            "npm",
            "create",
            "--yes",
            "vite@latest",
            name,
            "--",
            "--template",
            template,
            "--no-interactive",
        ]
    elif pkg_manager == "pnpm":
        cmd = [
            "pnpm",
            "create",
            "vite",
            name,
            "--template",
            template,
            "--no-interactive",
        ]
    elif pkg_manager == "yarn":
        cmd = [
            "yarn",
            "create",
            "vite",
            name,
            "--template",
            template,
            "--no-interactive",
        ]
    elif pkg_manager == "bun":
        cmd = [
            "bun",
            "create",
            "vite",
            name,
            "--template",
            template,
            "--no-interactive",
        ]
    else:
        raise ValueError("Unsupported package manager")

    run_quiet(cmd)
    update_client_build_config_for_static_output(name)

def create_config_toml(pkg_manager: str, framework: str, proj_name: str):
    doc = document()
    doc.add(comment("Auto-generated by ovl setup"))
    doc.add(nl())
    
    project = table()
    project.add('name', proj_name)
    project.add('entry_dir', 'web')
    project.add('entry_file', 'index.html')
    
    doc.add('project', project)
    doc.add(nl())

    window = table()
    window.add('width', 600)
    window.add('height', 400)
    window.add('x', 40)
    window.add('y', 40)
    window.add('movable', True)
    window.add('move_element', '')

    doc.add('window', window)
    doc.add(nl())

    build = table()
    build.add('framework', framework)
    build.add('package_manager', pkg_manager)
    build.add('frontend_output', 'build')
    build.add('build_dist', 'build/ovl')

    doc.add('build', build)

    file = TOMLFile(f'{proj_name}/ovl_config.toml')
    file.write(doc)

questions = [
    {
        "name": "project_name",
        "message": "Enter project name:",
        "type": "input",
        "validate": EmptyInputValidator(),
        "invalid_message": "Project name cannot be empty",
    },
    {
        "name": "package_manager",
        "message": "Select a package manager:",
        "type": "list",
        "choices": ["npm", "bun", "yarn", "pnpm"],
    },
    {
        "name": "framework",
        "message": "Select a web framework/library:",
        "type": "list",
        "choices": ["SvelteKit", "React", "Vue", "Solid", "Vanilla"],
    },
    {
        "name": "language",
        "message": "Select a frontend language:",
        "type": "list",
        "choices": ["TypeScript", "JavaScript"],
    },
    {
        "name": "confirmed",
        "message": "Confirm?",
        "type": "confirm",
        "default": True,
    },
]

def main():
    try:
        result = prompt(questions, vi_mode=True)

        if not result["confirmed"]:
            raise SystemExit(0)

        create_project(
            result['package_manager'],
            result['framework'].lower(),
            result['language'],
            result['project_name'],
        )  # pyright: ignore[reportArgumentType]
        create_config_toml(
            result['package_manager'],
            result['framework'].lower(),
            result['project_name'],
        )  # pyright: ignore[reportArgumentType]

    except InvalidArgument:
        print("No available choices")
    except FileNotFoundError as exc:
        print(exc)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}")


if __name__ == "__main__":
    main()
