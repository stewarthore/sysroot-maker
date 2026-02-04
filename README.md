# Sysroot-maker

A Python tool for creating cross-architecture sysroots suitable for building initramfs images. Uses `debootstrap --foreign` to populate sysroots **without requiring qemu**.

## Features

- ✅ Creates ARM64 sysroots without qemu (extensible to other architectures)
- ✅ Uses `debootstrap --foreign` for clean, minimal sysroots
- ✅ Unpacks Ubuntu kernel .deb packages (local or auto-downloaded)
- ✅ Configurable Ubuntu release and mirror
- ✅ Support for custom package lists
- ✅ Built-in initramfs package presets

## Requirements

- Python 3.13+
- `debootstrap` package
- `binutils` (for `ar` command)
- **Either** root/sudo privileges **OR** `fakeroot` package

```bash
# Required packages
sudo apt-get install debootstrap binutils

# Install fakeroot to run without sudo (recommended)
sudo apt-get install fakeroot
```

> **Note:** With `--foreign` mode, debootstrap only unpacks files without running configuration scripts. This works perfectly with `fakeroot`, eliminating the need for root privileges!

## Installation

```bash
# Clone and setup
cd sysroot-maker

# Run with fakeroot (no sudo needed!)
uv run sysroot_maker.py --help

# Or with sudo if fakeroot is not available
sudo uv run sysroot_maker.py --help
```

## Usage

### Basic Usage

```bash
# Create minimal arm64 sysroot (no sudo needed with fakeroot!)
uv run sysroot_maker.py --output /tmp/arm64-sysroot

# Create with verbose output
uv run sysroot_maker.py --output /tmp/arm64-sysroot --verbose
```

### With Package Options

```bash
# Include typical initramfs packages (busybox-static, klibc-utils, etc.)
uv run sysroot_maker.py --output /tmp/arm64-sysroot --initramfs-packages

# Add specific packages
uv run sysroot_maker.py --output /tmp/arm64-sysroot --packages vim curl

# Load packages from a file (one per line)
uv run sysroot_maker.py --output /tmp/arm64-sysroot --package-list packages.txt
```

### With Kernel Packages

```bash
# Extract local kernel .deb files
uv run sysroot_maker.py --output /tmp/arm64-sysroot \
  --kernel-deb linux-image-6.8.0-51-generic_6.8.0-51.52_arm64.deb \
  --kernel-deb linux-modules-6.8.0-51-generic_6.8.0-51.52_arm64.deb

# Auto-download kernel packages by version
uv run sysroot_maker.py --output /tmp/arm64-sysroot \
  --kernel-version 6.8.0-51-generic
```

### Advanced Options

```bash
# Specify Ubuntu release
uv run sysroot_maker.py --output /tmp/arm64-sysroot --release jammy

# Use custom mirror
uv run sysroot_maker.py --output /tmp/arm64-sysroot \
  --mirror http://ports.ubuntu.com/ubuntu-ports

# Clean existing directory before creation
uv run sysroot_maker.py --output /tmp/arm64-sysroot --clean

# Different architecture (for future support)
uv run sysroot_maker.py --output /tmp/armhf-sysroot --arch armhf
```

## Command-Line Options

```
Required:
  -o, --output DIR          Output directory path for the sysroot

Architecture & Release:
  --arch ARCH              Target architecture (default: arm64)
  --release RELEASE        Ubuntu release codename (default: noble)
  --mirror URL             Ubuntu mirror URL (auto-detected if not specified)

Packages:
  --packages PKG [PKG ...]       Additional packages to include
  --initramfs-packages           Include typical initramfs packages
  --package-list FILE            File with package names (one per line)

Kernel:
  --kernel-deb FILE              Local .deb file to extract (repeatable)
  --kernel-version VERSION       Kernel version to download (e.g., 6.8.0-51-generic)

Utilities:
  --clean                  Remove existing output directory
  -v, --verbose           Enable verbose output
```

## How It Works

1. **Validates dependencies**: Checks for `debootstrap` and `ar` command
2. **Runs debootstrap --foreign**: Creates base sysroot without qemu
   - Uses `--variant=minbase` for minimal installation
   - Stops before configuration phase (no qemu needed)
3. **Extracts kernel packages**: Unpacks .deb files using `ar` and `tar`
4. **Creates summary**: Shows what was installed

The resulting sysroot contains all files needed for building initramfs images but is **not bootable or configured** (by design).

## Package List File Format

Create a text file with one package name per line:

```
# my-packages.txt
busybox-static
klibc-utils
cryptsetup-bin
lvm2
# Comments are ignored
```

Use with: `--package-list my-packages.txt`

## Architecture Support

Currently optimized for ARM64, but designed to be extensible:

- `arm64`, `armhf`, `ppc64el`, `s390x`, `riscv64` → Ubuntu Ports mirror
- `amd64`, `i386` → Ubuntu main archive

Use `--arch` to specify target architecture.

## Why No Qemu?

Traditional cross-architecture sysroot creation often uses `debootstrap` with `qemu-user-static` to run configuration scripts. This approach:

- Uses `debootstrap --foreign` which stops after unpacking packages
- Skips the configuration phase entirely (no qemu needed)
- Produces a sysroot with all files but no system configuration
- Perfect for extracting files to build initramfs images

## Why Fakeroot?

With `--foreign` mode, debootstrap only:
- Downloads .deb packages
- Unpacks them into the target directory
- Does NOT run maintainer scripts or configuration

Since we're just unpacking files (not configuring a bootable system), `fakeroot` provides a fake root environment that satisfies debootstrap's ownership requirements without needing actual root privileges. This makes the tool much more convenient and safer to use!

## Troubleshooting

**Warning: Not running as root and fakeroot is not installed**
- Install fakeroot: `sudo apt-get install fakeroot`
- Or run with sudo: `sudo uv run sysroot_maker.py ...`

**Error: debootstrap is not installed**
```bash
sudo apt-get install debootstrap
```

**Error: ar command not found**
```bash
sudo apt-get install binutils
```

**Error: Output directory already exists**
- Use `--clean` flag to remove existing directory
- Or manually remove it: `rm -rf /path/to/sysroot`

**Kernel package download fails**
- Verify the kernel version exists for your architecture
- Try providing local .deb files with `--kernel-deb` instead
- Check mirror availability with `--verbose`

## Development

### Running Tests

The project includes comprehensive unit and integration tests using pytest.

**Install test dependencies:**
```bash
uv sync --extra test
```

**Run unit tests (default, fast, mocked):**
```bash
uv run pytest
# or explicitly:
uv run pytest tests/unit/
```

**Run integration tests (requires debootstrap, binutils, fakeroot):**
```bash
# Install system dependencies first
sudo apt-get install debootstrap binutils fakeroot

# Run integration tests
uv run pytest tests/integration/
```

**Run all tests:**
```bash
uv run pytest tests/
```

**Run tests with coverage:**
```bash
uv run pytest --cov=. --cov-report=term-missing
```

### Test Structure

```
tests/
├── unit/                   - Unit tests (default, fast, mocked)
│   ├── test_unit.py        - Core function unit tests
│   ├── test_unit_extended.py - Extended unit tests
│   └── test_cli.py         - CLI argument parsing tests
├── integration/            - Integration tests (real system calls)
│   └── test_integration.py - Integration tests with debootstrap
├── manual/                 - Manual tests (not automated)
│   └── README.md           - Manual testing guide
├── conftest.py             - Shared fixtures
└── fixtures/               - Test data files
```

### Continuous Integration

GitHub Actions CI runs automatically on push/PR:
- Unit tests (fast feedback)
- Integration tests (with system dependencies)
- Linting and format checking


## License

GNU GPL v3
