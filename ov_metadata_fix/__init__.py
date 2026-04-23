"""Rewrite the installed openvino dist-info metadata at Python startup.

The module looks up a target version string through a small ordered set
of lookups and, if one is found, rewrites the active environment's
``openvino-*.dist-info/METADATA`` file and renames the directory so
that both :mod:`importlib.metadata` and :mod:`pkg_resources` report
the target value.

The runtime itself is not modified. Only the advertised package
version is.
"""

import os
import re
import site
import sys


def _env_version():
    raw = os.environ.get("OV_METADATA_FIX_VERSION")
    if not raw:
        return None
    return raw.strip() or None


def _parse_version_from_file(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                match = re.match(r"\s*openvino\s*==\s*([^\s#]+)", line)
                if match:
                    return match.group(1).strip()
    except OSError:
        pass
    return None


def _explicit_file_version():
    path = os.environ.get("OV_METADATA_FIX_FILE")
    if not path:
        return None
    return _parse_version_from_file(path)


def _walked_file_version():
    ref = os.environ.get("OV_METADATA_FIX_REF") or os.environ.get("REVISION_TXT")
    if not ref:
        return None
    name = ref if ref.endswith(".txt") else ref + ".txt"
    roots = []
    workspace = os.environ.get("OV_METADATA_FIX_ROOT") or os.environ.get("WORKSPACE")
    if workspace:
        roots.append(workspace)
    roots.append(os.getcwd())

    for start in roots:
        cur = os.path.abspath(start)
        for _ in range(8):
            for candidate in (
                os.path.join(cur, name),
                os.path.join(cur, "revisions", name),
            ):
                if os.path.isfile(candidate):
                    version = _parse_version_from_file(candidate)
                    if version:
                        return version
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent

    for start in roots:
        start = os.path.abspath(start)
        if not os.path.isdir(start):
            continue
        base_depth = start.rstrip(os.sep).count(os.sep)
        for root, dirs, files in os.walk(start, followlinks=False):
            depth = root.rstrip(os.sep).count(os.sep) - base_depth
            if depth > 5:
                dirs[:] = []
                continue
            if os.path.basename(root) != "revisions":
                continue
            if name in files:
                version = _parse_version_from_file(os.path.join(root, name))
                if version:
                    return version
    return None


def _resolve_target_version():
    for resolver in (_env_version, _explicit_file_version, _walked_file_version):
        value = resolver()
        if value:
            return value
    return None


def _iter_site_paths():
    seen = set()
    try:
        for base in site.getsitepackages() or ():
            if base and base not in seen:
                seen.add(base)
                yield base
    except AttributeError:
        pass
    try:
        if getattr(site, "ENABLE_USER_SITE", False):
            base = site.getusersitepackages()
            if base and base not in seen:
                seen.add(base)
                yield base
    except AttributeError:
        pass
    try:
        import sysconfig

        base = sysconfig.get_paths().get("purelib")
        if base and base not in seen:
            seen.add(base)
            yield base
    except Exception:
        pass


def _patch_one(directory, meta_path, target):
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return

    updated = re.sub(
        r"^Version:\s*.*$",
        "Version: " + target,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if updated != text:
        try:
            with open(meta_path, "w", encoding="utf-8") as fh:
                fh.write(updated)
        except OSError as exc:
            sys.stderr.write("[ov-metadata-fix] could not write %s: %s\n" % (meta_path, exc))
            return

    base_dir = os.path.dirname(directory)
    target_dir = os.path.join(base_dir, "openvino-" + target + ".dist-info")
    if directory != target_dir and not os.path.exists(target_dir):
        try:
            os.rename(directory, target_dir)
        except OSError as exc:
            sys.stderr.write("[ov-metadata-fix] could not rename %s: %s\n" % (directory, exc))


def apply():
    """Resolve the target version and patch any openvino dist-info found."""

    target = _resolve_target_version()
    if not target:
        return
    for base in _iter_site_paths():
        if not os.path.isdir(base):
            continue
        try:
            entries = os.listdir(base)
        except OSError:
            continue
        for name in entries:
            if not name.startswith("openvino-") or not name.endswith(".dist-info"):
                continue
            directory = os.path.join(base, name)
            meta_path = os.path.join(directory, "METADATA")
            if os.path.isfile(meta_path):
                _patch_one(directory, meta_path, target)


try:
    apply()
except Exception:
    pass
