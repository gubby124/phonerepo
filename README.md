# Nepetas-Github

Emergency archive of Nepeta-related source projects and supporting tools.

This repository is organized as a multi-project archive. Each top-level folder is its own project, tweak, app, library, web tool, or support package. Most jailbreak tweak folders are Theos projects and should be built from inside their own folder.

## Contents

- `docs/PROJECTS.md` - generated index of the top-level projects and package metadata found in `control` files.
- `docs/Packages`, `docs/Packages.gz`, and `docs/debs/` - static Sileo/Cydia repository files for GitHub Pages.
- `PHPCyRepo/` - PHP Cydia repository web app.
- `Zebra/` - iOS package manager app source.
- `iOS-Blocks/` - iOS Blocks / Curago source and widget projects.
- Other top-level folders - individual tweaks, libraries, and utilities.

## Sileo Repo

After GitHub Pages is enabled for `main` / `docs`, add this source in Sileo:

```text
https://gubby124.github.io/phonerepo/
```

The repo metadata is generated from package payload folders. Source-only tweaks still need to be compiled into `.deb` files before they can be added to the Sileo repo.

## Setup

Clone the repository:

```powershell
git clone https://github.com/YOUR-USERNAME/nepsgit.git
cd nepsgit
```

For Theos tweak projects:

```powershell
cd Axon
make package
```

For Xcode projects, open the relevant `.xcodeproj` or `.xcworkspace` in Xcode on macOS.

For `PHPCyRepo/`, copy `config.php.example` to `config.php`, configure the database, and import `db.sql`.

## Notes

This repository contains both source code and a static package repo under `docs/`.
