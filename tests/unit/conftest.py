# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 sysroot-maker contributors
"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Provide a temporary output directory that auto-cleans."""
    output_dir = tmp_path / "test_sysroot"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def sample_package_list(tmp_path: Path) -> Path:
    """Create a sample package list file."""
    pkg_file = tmp_path / "test-packages.txt"
    pkg_file.write_text(
        """# Test package list
busybox-static
klibc-utils

# Another section
initramfs-tools-core
# Comment at end
"""
    )
    return pkg_file


@pytest.fixture
def empty_package_list(tmp_path: Path) -> Path:
    """Create an empty package list file."""
    pkg_file = tmp_path / "empty-packages.txt"
    pkg_file.write_text("# Only comments\n\n# Nothing else\n")
    return pkg_file


@pytest.fixture
def mock_deb_package(tmp_path: Path) -> Path:
    """Create a minimal mock .deb package for testing.

    This creates a valid .deb structure with control and data archives.
    """
    import subprocess

    deb_dir = tmp_path / "mock_deb"
    deb_dir.mkdir()

    # Create control file
    control_dir = deb_dir / "control"
    control_dir.mkdir()
    control_file = control_dir / "control"
    control_file.write_text(
        """Package: test-package
Version: 1.0.0
Architecture: arm64
Maintainer: Test <test@example.com>
Description: Test package
"""
    )

    # Create data files
    data_dir = deb_dir / "data"
    data_dir.mkdir()
    usr_bin = data_dir / "usr" / "bin"
    usr_bin.mkdir(parents=True)
    (usr_bin / "test-binary").write_text("#!/bin/sh\necho test\n")

    # Create control.tar.gz
    control_tar = deb_dir / "control.tar.gz"
    subprocess.run(
        ["tar", "-czf", str(control_tar), "-C", str(control_dir), "."],
        check=True,
        capture_output=True,
    )

    # Create data.tar.gz
    data_tar = deb_dir / "data.tar.gz"
    subprocess.run(
        ["tar", "-czf", str(data_tar), "-C", str(data_dir), "."],
        check=True,
        capture_output=True,
    )

    # Create debian-binary
    debian_binary = deb_dir / "debian-binary"
    debian_binary.write_text("2.0\n")

    # Create .deb using ar
    deb_file = tmp_path / "test-package_1.0.0_arm64.deb"
    subprocess.run(
        [
            "ar",
            "r",
            str(deb_file),
            str(debian_binary),
            str(control_tar),
            str(data_tar),
        ],
        check=True,
        capture_output=True,
    )

    return deb_file


@pytest.fixture
def mock_environment(monkeypatch):
    """Fixture to mock system environment variables and commands."""

    def _set_commands_available(*commands):
        """Mock which commands are available."""
        available_commands = set(commands)

        def mock_which(cmd):
            return f"/usr/bin/{cmd}" if cmd in available_commands else None

        monkeypatch.setattr("shutil.which", mock_which)

    return _set_commands_available
