from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from .authoring import (
    DevLinkError,
    DefaultsValidationError,
    link as dev_link,
    list_links as dev_list,
    normalize_provider_id,
    unlink as dev_unlink,
    validate_defaults_file,
)
from .core import Sigil
from .discovery import pep503_name
from .gui import launch_gui
from .resolver import (
    ProjectRootNotFoundError,
    default_provider_id,
    ensure_defaults_file,
    find_package_dir,
    find_project_root,
    read_dist_name_from_pyproject,
)


@click.group()
def cli() -> None:
    """Sigil command line interface."""


# ---------------------------------------------------------------------------
# Basic commands
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("key")
@click.option("--app", required=True)
def get(app: str, key: str) -> None:
    """Print the value for KEY."""

    sigil = Sigil(app)
    val = sigil.get_pref(key)
    if val is None:
        raise click.exceptions.Exit(1)
    click.echo(val)


@cli.command()
@click.argument("key")
@click.argument("value")
@click.option("--app", required=True)
@click.option("--scope", type=click.Choice(["user", "project"]), default="user")
def set(app: str, key: str, value: str, scope: str) -> None:
    """Set KEY to VALUE."""

    sigil = Sigil(app)
    sigil.set_pref(key, value, scope=scope)


@cli.group()
def secret() -> None:
    """Manage secret preferences."""


@secret.command("get")
@click.argument("key")
@click.option("--app", required=True)
@click.option("--reveal", is_flag=True, help="Print the secret value")
def secret_get(app: str, key: str, reveal: bool) -> None:
    sigil = Sigil(app)
    val = sigil.get_pref(key)
    if val is None:
        raise click.exceptions.Exit(1)
    click.echo(val if reveal else "*" * 8)


@secret.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--app", required=True)
def secret_set(app: str, key: str, value: str) -> None:
    sigil = Sigil(app)
    try:
        sigil.set_pref(key, value)
    except Exception:
        raise click.exceptions.Exit(1) from None


@secret.command("unlock")
@click.option("--app", required=True)
def secret_unlock(app: str) -> None:
    sigil = Sigil(app)
    sigil._secrets.unlock()


@cli.command()
@click.option("--app", required=True)
@click.option("--prefix", default="SIGIL_")
@click.option("--json", "as_json", is_flag=True)
def export(app: str, prefix: str, as_json: bool) -> None:
    """Export preferences as environment variables."""

    sigil = Sigil(app)
    mapping = sigil.export_env(prefix=prefix)
    if as_json:
        click.echo(json.dumps(mapping))
    else:
        for k, v in mapping.items():
            click.echo(f"{k}={v}")


@cli.command()
@click.option("--app")
@click.option("--include-sigil", is_flag=True)
@click.option("--no-remember", is_flag=True)
def gui(app: str | None, include_sigil: bool, no_remember: bool) -> None:
    """Launch the preferences GUI."""

    launch_gui(
        package=app,
        include_sigil=include_sigil,
        remember_state=not no_remember,
    )


@cli.command()
def setup() -> None:
    """Launch the defaults registration GUI."""

    from .gui.author import main as author_main

    author_main()


# ---------------------------------------------------------------------------
# Author commands
# ---------------------------------------------------------------------------


@cli.group()
def author() -> None:
    """Package author helpers."""


@author.command("register")
@click.option("--package-dir", type=click.Path(path_type=Path), help="Package directory")
@click.option("--defaults", type=click.Path(path_type=Path), help="Path to settings.ini")
@click.option("--provider", help="Override provider id")
@click.option("--auto", is_flag=True, help="Auto-detect from current directory")
@click.option("--no-validate", is_flag=True, help="Skip defaults validation")
def register(
    package_dir: Path | None,
    defaults: Path | None,
    provider: str | None,
    auto: bool,
    no_validate: bool,
) -> None:
    """Register package defaults for development."""

    if auto:
        try:
            root = find_project_root()
        except ProjectRootNotFoundError:
            root = Path.cwd()
        dist_name = read_dist_name_from_pyproject(root)
        pkg = find_package_dir(root, dist_name)
        if not pkg:
            click.echo("Could not auto-detect package directory", err=True)
            raise click.exceptions.Exit(2)
        provider_id = default_provider_id(pkg, dist_name)
        settings_path = ensure_defaults_file(pkg, provider_id)
        try:
            dev_link(provider_id, settings_path, validate=not no_validate)
        except DevLinkError as exc:
            click.echo(str(exc), err=True)
            raise click.exceptions.Exit(2) from None
        click.echo(f"Linked {provider_id} -> {settings_path}")
        return

    if bool(package_dir) == bool(defaults):
        click.echo("Use exactly one of --package-dir or --defaults", err=True)
        raise click.exceptions.Exit(2)

    if package_dir:
        chosen = package_dir
        if (chosen / "__init__.py").exists():
            pkg = chosen
        else:
            pkg = find_package_dir(chosen, None)
        if not pkg:
            click.echo("That folder doesn't look like a package", err=True)
            raise click.exceptions.Exit(2)
        try:
            root = find_project_root(pkg)
        except ProjectRootNotFoundError:
            root = pkg
        dist_name = read_dist_name_from_pyproject(root)
        provider_id = (
            normalize_provider_id(provider)
            if provider
            else default_provider_id(pkg, dist_name)
        )
        settings_path = ensure_defaults_file(pkg, provider_id)
        try:
            dev_link(provider_id, settings_path, validate=not no_validate)
        except DevLinkError as exc:
            click.echo(str(exc), err=True)
            raise click.exceptions.Exit(2) from None
        click.echo(f"Linked {provider_id} -> {settings_path}")
        return

    # defaults path branch
    assert defaults is not None
    if not provider:
        click.echo("--provider is required when using --defaults", err=True)
        raise click.exceptions.Exit(2)
    provider_id = normalize_provider_id(provider)
    try:
        dev_link(provider_id, defaults, validate=not no_validate)
    except DevLinkError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(2) from None
    click.echo(f"Linked {provider_id} -> {defaults}")


@author.command("link-defaults")
@click.argument("provider_id")
@click.argument("path", type=click.Path(path_type=Path))
def link_defaults(provider_id: str, path: Path) -> None:
    provider = pep503_name(provider_id)
    try:
        dev_link(provider, path)
    except (DefaultsValidationError, DevLinkError):
        raise click.exceptions.Exit(1) from None


@author.command("unlink-defaults")
@click.argument("provider_id")
def unlink_defaults(provider_id: str) -> None:
    provider = pep503_name(provider_id)
    ok = dev_unlink(provider)
    if not ok:
        raise click.exceptions.Exit(1)


@author.command()
@click.argument("provider_id")
@click.argument("path", type=click.Path(path_type=Path))
def validate(provider_id: str, path: Path) -> None:
    provider = pep503_name(provider_id)
    try:
        validate_defaults_file(path, provider)
    except DefaultsValidationError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(1) from None


@author.command("list")
@click.option("--existing-only", is_flag=True)
def list_links(existing_only: bool) -> None:
    entries = dev_list(must_exist_on_disk=existing_only)
    if not entries:
        click.echo("No dev links found")
        return
    for pid, path in sorted(entries.items()):
        status = "(ok)" if path.exists() else "(missing)"
        click.echo(f"{pid}: {path} {status}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    prog = os.path.basename(sys.argv[0]) or "sigil"
    if prog == "__main__.py":
        prog = "pysigil"
    try:
        cli.main(args=argv, prog_name=prog, standalone_mode=False)
    except SystemExit as exc:  # pragma: no cover - click always raises
        return exc.code
    return 0


if __name__ == "__main__":
    sys.exit(main())

