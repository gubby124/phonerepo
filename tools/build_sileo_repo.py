#!/usr/bin/env python3
import argparse
import bz2
import email.utils
import gzip
import hashlib
import io
import os
import re
import shutil
import tarfile
from pathlib import Path


TEXT_EXTENSIONS = {
    ".css",
    ".h",
    ".html",
    ".js",
    ".json",
    ".m",
    ".md",
    ".plist",
    ".strings",
    ".txt",
    ".xml",
}


def parse_control(text):
    fields = {}
    current = None
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith((" ", "\t")):
            if current:
                fields[current] += "\n" + line
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current = key
            fields[key] = value.strip()
    return fields


def safe_name(value):
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9.+~-]+", "_", value)
    return value.strip("_") or "package"


def has_payload(package_dir):
    return any(path.is_file() for path in package_dir.rglob("*") if "DEBIAN" not in path.parts)


def payload_size(package_dir):
    return sum(path.stat().st_size for path in package_dir.rglob("*") if path.is_file() and "DEBIAN" not in path.parts)


def file_mode(path, package_dir):
    relative = path.relative_to(package_dir).as_posix()
    name = path.name
    suffix = path.suffix.lower()
    if relative.startswith("DEBIAN/"):
        return 0o755 if name in {"preinst", "postinst", "prerm", "postrm"} else 0o644
    if suffix in TEXT_EXTENSIONS or suffix in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".car"}:
        return 0o644
    if suffix in {".dylib", ".tbd"}:
        return 0o644
    if "." not in name:
        return 0o755
    return 0o644


def add_tree_to_tar(tar, package_dir, include_debian):
    for path in sorted(package_dir.rglob("*")):
        relative = path.relative_to(package_dir).as_posix()
        is_debian = relative == "DEBIAN" or relative.startswith("DEBIAN/")
        if include_debian != is_debian:
            continue
        if relative == "DEBIAN":
            continue
        if relative.startswith("DEBIAN/") and path.name == ".DS_Store":
            continue

        archive_name = "./" + relative.removeprefix("DEBIAN/")
        info = tar.gettarinfo(str(path), archive_name)
        info.uid = 0
        info.gid = 0
        info.uname = "root"
        info.gname = "wheel"
        info.mode = 0o755 if path.is_dir() else file_mode(path, package_dir)

        if path.is_file():
            with path.open("rb") as handle:
                tar.addfile(info, handle)
        else:
            tar.addfile(info)


def make_tar_gz(package_dir, include_debian):
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            add_tree_to_tar(tar, package_dir, include_debian)
    return stream.getvalue()


def ar_member(name, data):
    encoded = name.encode("ascii")
    if len(encoded) > 16:
        raise ValueError(f"ar member name too long: {name}")
    header = (
        encoded.ljust(16, b" ")
        + b"0".ljust(12, b" ")
        + b"0".ljust(6, b" ")
        + b"0".ljust(6, b" ")
        + b"100644".ljust(8, b" ")
        + str(len(data)).encode("ascii").ljust(10, b" ")
        + b"`\n"
    )
    padding = b"\n" if len(data) % 2 else b""
    return header + data + padding


def write_deb(package_dir, output_dir):
    control_path = package_dir / "DEBIAN" / "control"
    control_text = control_path.read_text(encoding="utf-8", errors="replace").strip() + "\n"
    fields = parse_control(control_text)
    package = fields.get("Package", package_dir.name)
    version = fields.get("Version", "0")
    architecture = fields.get("Architecture", "iphoneos-arm")
    deb_name = f"{safe_name(package)}_{safe_name(version)}_{safe_name(architecture)}.deb"
    deb_path = output_dir / deb_name

    control_tar = make_tar_gz(package_dir, include_debian=True)
    data_tar = make_tar_gz(package_dir, include_debian=False)

    data = (
        b"!<arch>\n"
        + ar_member("debian-binary", b"2.0\n")
        + ar_member("control.tar.gz", control_tar)
        + ar_member("data.tar.gz", data_tar)
    )
    deb_path.write_bytes(data)
    return deb_path, control_text, fields


def checksum(path, algorithm):
    h = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def choose_package_dirs(package_root):
    candidates = []
    for package_dir in sorted(path for path in package_root.iterdir() if path.is_dir()):
        control_path = package_dir / "DEBIAN" / "control"
        if not control_path.exists() or not has_payload(package_dir):
            continue
        control_text = control_path.read_text(encoding="utf-8", errors="replace")
        fields = parse_control(control_text)
        key = (fields.get("Package", package_dir.name).lower(), fields.get("Version", "0"))
        candidates.append((key, payload_size(package_dir), package_dir))

    chosen = {}
    for key, size, package_dir in candidates:
        if key not in chosen or size > chosen[key][0]:
            chosen[key] = (size, package_dir)
    return [value[1] for key, value in sorted(chosen.items())]


def package_record(control_text, deb_path, output_root):
    relative = deb_path.relative_to(output_root).as_posix()
    size = deb_path.stat().st_size
    record = control_text.strip() + "\n"
    record += f"Filename: {relative}\n"
    record += f"Size: {size}\n"
    record += f"MD5sum: {checksum(deb_path, 'md5')}\n"
    record += f"SHA1: {checksum(deb_path, 'sha1')}\n"
    record += f"SHA256: {checksum(deb_path, 'sha256')}\n"
    return record


def write_release(output_root, packages_files):
    now = email.utils.formatdate(usegmt=True)
    lines = [
        "Origin: phonerepo",
        "Label: phonerepo",
        "Suite: stable",
        "Version: 1.0",
        "Codename: ios",
        "Architectures: iphoneos-arm",
        "Components: main",
        "Description: gubby124 Sileo repository",
        f"Date: {now}",
        "MD5Sum:",
    ]
    for path in packages_files:
        rel = path.relative_to(output_root).as_posix()
        lines.append(f" {checksum(path, 'md5')} {path.stat().st_size:16d} {rel}")
    lines.append("SHA1:")
    for path in packages_files:
        rel = path.relative_to(output_root).as_posix()
        lines.append(f" {checksum(path, 'sha1')} {path.stat().st_size:16d} {rel}")
    lines.append("SHA256:")
    for path in packages_files:
        rel = path.relative_to(output_root).as_posix()
        lines.append(f" {checksum(path, 'sha256')} {path.stat().st_size:16d} {rel}")
    (output_root / "Release").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index(output_root, repo_url, package_count):
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>phonerepo</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 40px; line-height: 1.45; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }}
    a.button {{ display: inline-block; margin: 10px 0; padding: 10px 14px; background: #111827; color: white; text-decoration: none; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>phonerepo</h1>
  <p>Sileo/Cydia repository hosted on GitHub Pages.</p>
  <p><strong>Repo URL:</strong> <code>{repo_url}</code></p>
  <p><a class="button" href="sileo://source/{repo_url}">Add to Sileo</a></p>
  <p>Packages published: {package_count}</p>
</body>
</html>
"""
    (output_root / "index.html").write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-folders", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo-url", required=True)
    args = parser.parse_args()

    output = args.output
    debs_dir = output / "debs"
    if debs_dir.exists():
        shutil.rmtree(debs_dir)
    debs_dir.mkdir(parents=True, exist_ok=True)

    package_dirs = choose_package_dirs(args.package_folders)
    records = []
    for package_dir in package_dirs:
        deb_path, control_text, fields = write_deb(package_dir, debs_dir)
        records.append(package_record(control_text, deb_path, output))

    packages = "\n".join(records) + "\n"
    packages_path = output / "Packages"
    packages_path.write_text(packages, encoding="utf-8")
    (output / "Packages.gz").write_bytes(gzip.compress(packages.encode("utf-8"), mtime=0))
    (output / "Packages.bz2").write_bytes(bz2.compress(packages.encode("utf-8")))
    (output / ".nojekyll").write_text("", encoding="utf-8")
    write_release(output, [packages_path, output / "Packages.gz", output / "Packages.bz2"])
    write_index(output, args.repo_url, len(records))

    print(f"Built {len(records)} packages into {output}")


if __name__ == "__main__":
    main()
