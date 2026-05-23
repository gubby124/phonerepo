#!/usr/bin/env python3
import argparse
import bz2
import email.utils
import gzip
import hashlib
import io
import shutil
import tarfile
from pathlib import Path


def read_ar_members(path):
    data = path.read_bytes()
    if not data.startswith(b"!<arch>\n"):
        raise ValueError(f"{path} is not an ar/deb archive")

    offset = 8
    while offset + 60 <= len(data):
        header = data[offset : offset + 60]
        offset += 60
        name = header[:16].decode("ascii", errors="replace").strip()
        size = int(header[48:58].decode("ascii").strip())
        content = data[offset : offset + size]
        offset += size + (size % 2)
        yield name.rstrip("/"), content


def extract_control_text(deb_path):
    for name, content in read_ar_members(deb_path):
        if name == "control.tar.gz":
            mode = "r:gz"
        elif name == "control.tar.xz":
            mode = "r:xz"
        elif name == "control.tar.bz2":
            mode = "r:bz2"
        else:
            continue

        with tarfile.open(fileobj=io.BytesIO(content), mode=mode) as tar:
            for member in tar.getmembers():
                if member.name.lstrip("./") == "control":
                    handle = tar.extractfile(member)
                    if handle is None:
                        break
                    return handle.read().decode("utf-8", errors="replace").strip() + "\n"
    raise ValueError(f"{deb_path} does not contain control metadata")


def checksum(path, algorithm):
    h = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package_record(deb_path, output_root):
    control_text = extract_control_text(deb_path)
    relative = deb_path.relative_to(output_root).as_posix()
    size = deb_path.stat().st_size
    return (
        control_text.strip()
        + "\n"
        + f"Filename: {relative}\n"
        + f"Size: {size}\n"
        + f"MD5sum: {checksum(deb_path, 'md5')}\n"
        + f"SHA1: {checksum(deb_path, 'sha1')}\n"
        + f"SHA256: {checksum(deb_path, 'sha256')}\n"
    )


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


def mirror_to_docs(output_root):
    docs = output_root / "docs"
    docs.mkdir(exist_ok=True)
    for name in ["Packages", "Packages.gz", "Packages.bz2", "Release", "index.html", ".nojekyll"]:
        shutil.copy2(output_root / name, docs / name)
    docs_debs = docs / "debs"
    if docs_debs.exists():
        shutil.rmtree(docs_debs)
    shutil.copytree(output_root / "debs", docs_debs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("."))
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--mirror-docs", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    debs_dir = output / "debs"
    records = [package_record(path, output) for path in sorted(debs_dir.glob("*.deb"))]
    packages = "\n".join(records) + "\n"

    packages_path = output / "Packages"
    packages_path.write_text(packages, encoding="utf-8")
    (output / "Packages.gz").write_bytes(gzip.compress(packages.encode("utf-8"), mtime=0))
    (output / "Packages.bz2").write_bytes(bz2.compress(packages.encode("utf-8")))
    (output / ".nojekyll").write_text("", encoding="utf-8")
    write_release(output, [packages_path, output / "Packages.gz", output / "Packages.bz2"])
    write_index(output, args.repo_url, len(records))

    if args.mirror_docs:
        mirror_to_docs(output)

    print(f"Indexed {len(records)} packages")


if __name__ == "__main__":
    main()
