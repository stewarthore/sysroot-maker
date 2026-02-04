#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 sysroot-maker contributors
"""
Sysroot Setup Script - Creates cross-architecture sysroots for building initramfs
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import List, Optional

# Default initramfs packages
INITRAMFS_PACKAGES = [
    "busybox-static",
    "klibc-utils",
    "initramfs-tools-core",
]


def get_mirror_for_arch(arch: str) -> str:
    """Return appropriate Ubuntu mirror URL for the given architecture."""
    if arch in ["arm64", "armhf", "ppc64el", "s390x", "riscv64"]:
        return "http://ports.ubuntu.com/ubuntu-ports"
    else:
        return "http://archive.ubuntu.com/ubuntu"


def is_command_available(name: str) -> bool:
    """Check if a command is available on the system."""
    return shutil.which(name) is not None


def is_root() -> bool:
    """Check if running as root."""
    return os.geteuid() == 0


def read_package_list(file_path: str) -> List[str]:
    """Read package names from a file, one per line, ignoring empty lines and
    comments.
    """
    packages = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    packages.append(line)
    except FileNotFoundError:
        print(f"Error: Package list file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading package list file: {e}", file=sys.stderr)
        sys.exit(1)
    return packages


def run_debootstrap(
    output_dir: str,
    arch: str,
    release: str,
    mirror: str,
    packages: List[str],
    verbose: bool = False,
    use_fakeroot: bool = False,
) -> bool:
    """Run debootstrap --foreign to create the sysroot."""
    cmd = []

    if use_fakeroot:
        cmd.append("fakeroot")

    cmd.extend(["debootstrap", "--foreign", f"--arch={arch}", "--variant=minbase"])

    if packages:
        cmd.append(f"--include={','.join(packages)}")

    cmd.extend([release, output_dir, mirror])

    if verbose:
        print(f"Running: {' '.join(cmd)}")
        if use_fakeroot:
            print("(Using fakeroot - no root privileges required)")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if not verbose else None,
            stderr=subprocess.PIPE if not verbose else None,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"Error: debootstrap failed with exit code {result.returncode}",
                file=sys.stderr,
            )
            if not verbose:
                print(
                    "Run with --verbose to see detailed error output", file=sys.stderr
                )
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
            if not use_fakeroot:
                print("\nCommon causes:", file=sys.stderr)
                print(
                    "  - Not running as root and fakeroot not available",
                    file=sys.stderr,
                )
                print("  - Invalid release name or architecture", file=sys.stderr)
                print("  - Network connectivity issues", file=sys.stderr)
            return False

        return True
    except subprocess.SubprocessError as e:
        print(f"Error running debootstrap: {e}", file=sys.stderr)
        return False


def extract_deb_package(deb_path: str, target_dir: str, verbose: bool = False) -> bool:
    """Extract a .deb package into the target directory."""
    if not os.path.isfile(deb_path):
        print(f"Error: .deb file not found: {deb_path}", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        if verbose:
            print(f"Extracting {os.path.basename(deb_path)}...")

        # Extract the .deb archive
        try:
            subprocess.run(
                ["ar", "x", deb_path],
                cwd=tmpdir,
                check=True,
                capture_output=not verbose,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error extracting .deb with ar: {e}", file=sys.stderr)
            return False

        # Find the data archive
        data_archives = list(Path(tmpdir).glob("data.tar.*"))
        if not data_archives:
            print(f"Error: No data.tar.* found in {deb_path}", file=sys.stderr)
            return False

        data_archive = data_archives[0]

        # Extract data archive into target directory
        try:
            subprocess.run(
                ["tar", "-xf", str(data_archive), "-C", target_dir],
                check=True,
                capture_output=not verbose,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error extracting data archive: {e}", file=sys.stderr)
            return False

    return True


def validate_deb_architecture(
    deb_path: str, expected_arch: str, verbose: bool = False
) -> bool:
    """Validate that a .deb package is for the expected architecture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Extract control archive
            subprocess.run(
                ["ar", "x", deb_path], cwd=tmpdir, check=True, capture_output=True
            )

            # Find and extract control archive
            control_archives = list(Path(tmpdir).glob("control.tar.*"))
            if not control_archives:
                if verbose:
                    print(f"Warning: No control archive found in {deb_path}")
                return True  # Assume valid if we can't check

            # Extract control file
            result = subprocess.run(
                ["tar", "-xf", str(control_archives[0]), "-O", "./control"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )

            # Parse architecture from control file
            for line in result.stdout.split("\n"):
                if line.startswith("Architecture:"):
                    arch = line.split(":", 1)[1].strip()
                    # 'all' architecture packages are valid for any arch
                    if arch == "all" or arch == expected_arch:
                        return True
                    else:
                        print(
                            f"Error: Package {deb_path} is for {arch}, "
                            f"expected {expected_arch}",
                            file=sys.stderr,
                        )
                        return False

            if verbose:
                print(f"Warning: Could not determine architecture for {deb_path}")
            return True

        except subprocess.CalledProcessError:
            if verbose:
                print(f"Warning: Could not validate architecture for {deb_path}")
            return True  # Assume valid if validation fails


def download_kernel_package(
    package_name: str,
    version: str,
    arch: str,
    release: str,
    mirror: str,
    target_dir: str,
    verbose: bool = False,
) -> Optional[str]:
    """Download a kernel package from Ubuntu repositories."""
    # Construct package URL
    pool_url = f"{mirror}/pool/main/l/linux/"

    # Try to find the package
    full_package_name = f"{package_name}_{version}_{arch}.deb"
    package_url = f"{pool_url}{full_package_name}"

    target_path = os.path.join(target_dir, full_package_name)

    if verbose:
        print(f"Downloading {package_url}...")

    try:
        urllib.request.urlretrieve(package_url, target_path)
        return target_path
    except Exception as e:
        if verbose:
            print(f"Warning: Could not download {package_url}: {e}")
        return None


def check_disk_space(path: str, required_gb: float = 2.0) -> bool:
    """Check if there's enough disk space available."""
    try:
        stat = os.statvfs(path)
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        return available_gb >= required_gb
    except OSError:
        return True  # Assume OK if we can't check


def main():
    parser = argparse.ArgumentParser(
        description="Create cross-architecture sysroots for building initramfs (no qemu required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Minimal arm64 sysroot
  %(prog)s --output /tmp/arm64-sysroot

  # With initramfs packages
  %(prog)s --output /tmp/arm64-sysroot --initramfs-packages

  # With custom packages and kernel
  %(prog)s -o /tmp/arm64-sysroot --package-list packages.txt --kernel-version 6.8.0-51-generic

  # With local kernel .deb files
  %(prog)s -o /tmp/arm64-sysroot --kernel-deb linux-image-*.deb --kernel-deb linux-modules-*.deb
        """,
    )

    # Required arguments
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory path for the sysroot"
    )

    # Architecture and release options
    parser.add_argument(
        "--arch", default="arm64", help="Target architecture (default: arm64)"
    )
    parser.add_argument(
        "--release", default="noble", help="Ubuntu release codename (default: noble)"
    )
    parser.add_argument(
        "--mirror",
        help="Ubuntu mirror URL (auto-detected based on architecture if not specified)",
    )

    # Package management options
    parser.add_argument("--packages", nargs="+", help="Additional packages to include")
    parser.add_argument(
        "--initramfs-packages",
        action="store_true",
        help="Include typical initramfs packages (busybox-static, klibc-utils, etc.)",
    )
    parser.add_argument(
        "--package-list", help="File containing package names (one per line)"
    )

    # Kernel options
    parser.add_argument(
        "--kernel-deb",
        action="append",
        dest="kernel_debs",
        help="Local .deb file to extract into sysroot (can be specified multiple times)",
    )
    parser.add_argument(
        "--kernel-version",
        help="Kernel version to download from Ubuntu repos (e.g., 6.8.0-51-generic)",
    )

    # Utility options
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing output directory before creation",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Validate dependencies
    if not is_command_available("debootstrap"):
        print(
            "Error: debootstrap is not installed. Please install it first:",
            file=sys.stderr,
        )
        print("  sudo apt-get install debootstrap", file=sys.stderr)
        sys.exit(1)

    if not is_command_available("ar"):
        print("Error: ar command not found. Please install binutils:", file=sys.stderr)
        print("  sudo apt-get install binutils", file=sys.stderr)
        sys.exit(1)

    # Determine if we should use fakeroot
    use_fakeroot = False
    running_as_root = is_root()

    if not running_as_root:
        if is_command_available("fakeroot"):
            use_fakeroot = True
            if args.verbose:
                print("Not running as root, but fakeroot is available - using fakeroot")
        else:
            print(
                "Warning: Not running as root and fakeroot is not installed",
                file=sys.stderr,
            )
            print("This will likely fail. Options:", file=sys.stderr)
            print("  1. Run with sudo: sudo python3 sysroot_maker.py ...", file=sys.stderr)
            print(
                "  2. Install fakeroot: sudo apt-get install fakeroot", file=sys.stderr
            )
            print("", file=sys.stderr)

    # Determine mirror
    mirror = args.mirror or get_mirror_for_arch(args.arch)

    # Handle output directory
    output_dir = os.path.abspath(args.output)

    if os.path.exists(output_dir):
        if args.clean:
            if args.verbose:
                print(f"Removing existing directory: {output_dir}")
            shutil.rmtree(output_dir)
        else:
            print(
                f"Error: Output directory already exists: {output_dir}", file=sys.stderr
            )
            print("Use --clean to remove it first", file=sys.stderr)
            sys.exit(1)

    # Check disk space
    parent_dir = os.path.dirname(output_dir) or "."
    if not check_disk_space(parent_dir, required_gb=2.0):
        print("Warning: Less than 2GB of disk space available", file=sys.stderr)

    # Build package list
    packages = []
    if args.packages:
        packages.extend(args.packages)
    if args.initramfs_packages:
        packages.extend(INITRAMFS_PACKAGES)
    if args.package_list:
        packages.extend(read_package_list(args.package_list))

    # Remove duplicates while preserving order
    seen = set()
    packages = [p for p in packages if not (p in seen or seen.add(p))]

    if args.verbose:
        print(f"Creating {args.arch} sysroot at: {output_dir}")
        print(f"Release: {args.release}")
        print(f"Mirror: {mirror}")
        if packages:
            print(f"Additional packages: {', '.join(packages)}")

    # Run debootstrap
    print("Running debootstrap (this may take several minutes)...")
    if not run_debootstrap(
        output_dir,
        args.arch,
        args.release,
        mirror,
        packages,
        args.verbose,
        use_fakeroot,
    ):
        sys.exit(1)

    print(f"✓ Debootstrap completed successfully")

    # Handle kernel packages
    kernel_debs_to_extract = []

    if args.kernel_debs:
        kernel_debs_to_extract.extend(args.kernel_debs)

    if args.kernel_version:
        print(
            f"Attempting to download kernel packages for version {args.kernel_version}..."
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel_packages = [
                f"linux-image-{args.kernel_version}",
                f"linux-modules-{args.kernel_version}",
            ]

            for pkg_name in kernel_packages:
                deb_path = download_kernel_package(
                    pkg_name.rsplit("_", 1)[0],  # Remove any version suffix
                    args.kernel_version,
                    args.arch,
                    args.release,
                    mirror,
                    tmpdir,
                    args.verbose,
                )
                if deb_path:
                    kernel_debs_to_extract.append(deb_path)

    # Extract kernel packages
    if kernel_debs_to_extract:
        print(f"Extracting {len(kernel_debs_to_extract)} kernel package(s)...")
        for deb_path in kernel_debs_to_extract:
            # Validate architecture
            if not validate_deb_architecture(deb_path, args.arch, args.verbose):
                print(
                    f"Skipping {deb_path} due to architecture mismatch", file=sys.stderr
                )
                continue

            if not extract_deb_package(deb_path, output_dir, args.verbose):
                print(f"Warning: Failed to extract {deb_path}", file=sys.stderr)
            else:
                print(f"  ✓ Extracted {os.path.basename(deb_path)}")

    # Summary
    print("\n" + "=" * 60)
    print("Sysroot creation completed successfully!")
    print("=" * 60)
    print(f"Location: {output_dir}")
    print(f"Architecture: {args.arch}")
    print(f"Release: {args.release}")

    if packages:
        print(f"Additional packages: {len(packages)}")

    if kernel_debs_to_extract:
        print(f"Kernel packages: {len(kernel_debs_to_extract)}")

    print("\nNote: This is a --foreign sysroot (not configured, no qemu used)")
    print("      It contains all files needed for building initramfs images.")
    print("=" * 60)


if __name__ == "__main__":
    main()
