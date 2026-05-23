# Nepetas-Github

Emergency archive of Nepeta-related source projects and supporting tools.

This repository is organized as a multi-project archive. Each top-level folder is its own project, tweak, app, library, web tool, or support package. Most jailbreak tweak folders are Theos projects and should be built from inside their own folder.

## Contents

- `docs/PROJECTS.md` - generated index of the top-level projects and package metadata found in `control` files.
- `PHPCyRepo/` - PHP Cydia repository web app.
- `Zebra/` - iOS package manager app source.
- `iOS-Blocks/` - iOS Blocks / Curago source and widget projects.
- Other top-level folders - individual tweaks, libraries, and utilities.

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

This is source-first GitHub structure. It is different from a YouRepo upload structure: YouRepo wants compiled `.deb` files or package-root zips with `DEBIAN/control`, while GitHub should usually store source code, documentation, and build scripts.
