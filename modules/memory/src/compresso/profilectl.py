#!/usr/bin/env python3
"""Explicit, configuration-only profile inspection and selection for compressoctl."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

try:
    from .memoryd import MemoryErrorSafe, PROFILES, load_config, validate_config
except ImportError:  # installed as a standalone script in /usr/libexec/compresso
    from memoryd import MemoryErrorSafe, PROFILES, load_config, validate_config


DEFAULT_CONFIG = "/etc/compresso/memory.conf"
PROFILE_INFO = {
    "zram-fast": {
        "description": "ZRAM as the primary compressed swap; expects Zswap disabled.",
        "requirements": [],
    },
    "zswap-first": {
        "description": "Zswap backed by an explicitly configured swap device or file.",
        "requirements": ["BACKING_SWAP must be set explicitly"],
    },
    "hybrid-exp": {
        "description": "Experimental ZRAM plus Zswap configuration.",
        "requirements": ["BACKING_SWAP must be empty", "Zswap kernel interfaces must exist at apply time"],
    },
}


class ProfileConfigError(RuntimeError):
    """A profile change cannot be made safely."""


def list_profiles():
    return [
        {"name": name, **details}
        for name, details in PROFILE_INFO.items()
    ]


def _read_config(path):
    config_path = Path(path)
    try:
        metadata = config_path.lstat()
    except FileNotFoundError as exc:
        raise ProfileConfigError(f"no existe el archivo de configuración: {config_path}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise ProfileConfigError("se rechaza una configuración que sea enlace simbólico")
    if not stat.S_ISREG(metadata.st_mode):
        raise ProfileConfigError("la configuración debe ser un archivo regular")
    try:
        config = load_config(config_path)
        raw = config_path.read_text(encoding="utf-8")
    except (MemoryErrorSafe, OSError, UnicodeError) as exc:
        raise ProfileConfigError(f"configuración inválida o ilegible: {exc}") from exc
    return config_path, metadata, config, raw


def show_profile(path=DEFAULT_CONFIG):
    config_path, _metadata, config, _raw = _read_config(path)
    return {
        "config_path": str(config_path),
        "profile": config["PROFILE"],
        "effect": "configuration-only",
        "applied": False,
    }


def _replace_profile_line(raw, profile):
    lines = raw.splitlines(keepends=True)
    found = False
    for index, line in enumerate(lines):
        key, separator, _value = line.partition("=")
        if separator and key.strip() == "PROFILE":
            newline = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
            lines[index] = f"{key}{separator}{profile}{newline}"
            found = True
    if not found:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += "\n"
        lines.append(f"PROFILE={profile}\n")
    return "".join(lines)


def _atomic_replace(path, content, metadata):
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode))
            current_uid = os.geteuid()
            if current_uid == 0:
                os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
            else:
                if metadata.st_uid != current_uid:
                    raise PermissionError("no se puede preservar el propietario del archivo")
                temporary_gid = os.fstat(stream.fileno()).st_gid
                if temporary_gid != metadata.st_gid:
                    os.fchown(stream.fileno(), -1, metadata.st_gid)
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def set_profile(path, profile):
    if profile not in PROFILES:
        raise ProfileConfigError(
            "perfil no reconocido; opciones: " + ", ".join(sorted(PROFILES))
        )

    config_path, metadata, current, raw = _read_config(path)
    candidate = dict(current)
    candidate["PROFILE"] = profile
    try:
        validate_config(candidate)
    except MemoryErrorSafe as exc:
        raise ProfileConfigError(f"el perfil no es compatible con la configuración actual: {exc}") from exc

    previous = current["PROFILE"]
    if previous == profile:
        return {
            "config_path": str(config_path),
            "previous_profile": previous,
            "profile": profile,
            "changed": False,
            "effect": "configuration-only",
            "applied": False,
        }

    updated = _replace_profile_line(raw, profile)
    try:
        _atomic_replace(config_path, updated, metadata)
    except OSError as exc:
        raise ProfileConfigError(f"no se pudo guardar la configuración de forma atómica: {exc}") from exc

    return {
        "config_path": str(config_path),
        "previous_profile": previous,
        "profile": profile,
        "changed": True,
        "effect": "configuration-only",
        "applied": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="listar perfiles disponibles")
    subparsers.add_parser("show", help="mostrar el perfil persistido")
    set_parser = subparsers.add_parser("set", help="guardar un perfil para una aplicación posterior")
    set_parser.add_argument("profile", choices=sorted(PROFILES))
    args = parser.parse_args(argv)

    try:
        if args.command == "list":
            result = {"profiles": list_profiles(), "effect": "read-only"}
        elif args.command == "show":
            result = show_profile(args.config)
        else:
            result = set_profile(args.config, args.profile)
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.command == "set":
            if result["changed"]:
                print(
                    "Perfil guardado solo en configuración. No se aplicó al kernel, "
                    "no se activó/desactivó swap y no se reinició ningún servicio.",
                    file=sys.stderr,
                )
            else:
                print("El perfil ya estaba configurado; no se realizaron cambios.", file=sys.stderr)
        return 0
    except (ProfileConfigError, OSError) as exc:
        print(f"compressoctl profile: ERROR: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
