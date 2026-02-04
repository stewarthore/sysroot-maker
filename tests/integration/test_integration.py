# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 sysroot-maker contributors
"""Integration tests for sysroot_maker (requires real system dependencies)."""

from pathlib import Path

import pytest

import sysroot_maker


@pytest.mark.integration
@pytest.mark.requires_debootstrap
class TestDebExtraction:
    """Test .deb package extraction with real files."""

    def test_extract_real_deb_package(self, mock_deb_package, temp_output_dir):
        """Test extracting a real .deb package."""
        result = sysroot_maker.extract_deb_package(
            str(mock_deb_package),
            str(temp_output_dir),
            verbose=True,
        )

        assert result is True
        # Check that files were extracted
        extracted_file = temp_output_dir / "usr" / "bin" / "test-binary"
        assert extracted_file.exists()
        assert extracted_file.read_text() == "#!/bin/sh\necho test\n"

    def test_extract_nonexistent_deb(self, temp_output_dir):
        """Test extracting a non-existent .deb file."""
        result = sysroot_maker.extract_deb_package(
            "/nonexistent/package.deb",
            str(temp_output_dir),
            verbose=False,
        )

        assert result is False

    def test_validate_deb_architecture_real(self, mock_deb_package):
        """Test validating .deb architecture with real package."""
        result = sysroot_maker.validate_deb_architecture(
            str(mock_deb_package),
            "arm64",
            verbose=True,
        )

        assert result is True

    def test_validate_deb_architecture_mismatch(self, mock_deb_package):
        """Test architecture mismatch detection."""
        result = sysroot_maker.validate_deb_architecture(
            str(mock_deb_package),
            "amd64",  # Package is arm64
            verbose=True,
        )

        assert result is False


@pytest.mark.integration
@pytest.mark.requires_debootstrap
@pytest.mark.slow
class TestDebootstrapIntegration:
    """Test debootstrap integration (slow tests)."""

    def test_run_debootstrap_minimal(self, temp_output_dir):
        """Test running debootstrap with minimal configuration."""
        # Skip if not running as root or without fakeroot
        if not sysroot_maker.is_root() and not sysroot_maker.is_command_available(
            "fakeroot"
        ):
            pytest.skip("Requires root or fakeroot")

        if not sysroot_maker.is_command_available("debootstrap"):
            pytest.skip("debootstrap not available")

        use_fakeroot = not sysroot_maker.is_root()

        result = sysroot_maker.run_debootstrap(
            output_dir=str(temp_output_dir),
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=[],
            verbose=True,
            use_fakeroot=use_fakeroot,
        )

        assert result is True
        # Check that basic directories were created
        assert (temp_output_dir / "usr").exists()
        assert (temp_output_dir / "var").exists()
        assert (temp_output_dir / "etc").exists()

    def test_run_debootstrap_with_packages(self, temp_output_dir):
        """Test running debootstrap with additional packages."""
        # Skip if not running as root or without fakeroot
        if not sysroot_maker.is_root() and not sysroot_maker.is_command_available(
            "fakeroot"
        ):
            pytest.skip("Requires root or fakeroot")

        if not sysroot_maker.is_command_available("debootstrap"):
            pytest.skip("debootstrap not available")

        use_fakeroot = not sysroot_maker.is_root()

        # Use a small package that's quick to download
        result = sysroot_maker.run_debootstrap(
            output_dir=str(temp_output_dir),
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=["base-files"],  # Minimal package
            verbose=True,
            use_fakeroot=use_fakeroot,
        )

        assert result is True
        assert (temp_output_dir / "usr").exists()

    def test_run_debootstrap_invalid_release(self, temp_output_dir):
        """Test that invalid release is handled."""
        if not sysroot_maker.is_root() and not sysroot_maker.is_command_available(
            "fakeroot"
        ):
            pytest.skip("Requires root or fakeroot")

        if not sysroot_maker.is_command_available("debootstrap"):
            pytest.skip("debootstrap not available")

        use_fakeroot = not sysroot_maker.is_root()

        result = sysroot_maker.run_debootstrap(
            output_dir=str(temp_output_dir),
            arch="arm64",
            release="nonexistent-release",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=[],
            verbose=False,
            use_fakeroot=use_fakeroot,
        )

        assert result is False


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEnd:
    """End-to-end integration tests."""

    def test_create_minimal_sysroot_end_to_end(self, temp_output_dir):
        """Test creating a minimal sysroot end-to-end."""
        if not sysroot_maker.is_command_available("debootstrap"):
            pytest.skip("debootstrap not available")

        if not sysroot_maker.is_command_available("ar"):
            pytest.skip("ar command not available")

        if not sysroot_maker.is_root() and not sysroot_maker.is_command_available(
            "fakeroot"
        ):
            pytest.skip("Requires root or fakeroot")

        # Run the actual debootstrap
        use_fakeroot = not sysroot_maker.is_root()
        mirror = sysroot_maker.get_mirror_for_arch("arm64")

        success = sysroot_maker.run_debootstrap(
            output_dir=str(temp_output_dir),
            arch="arm64",
            release="noble",
            mirror=mirror,
            packages=[],
            verbose=True,
            use_fakeroot=use_fakeroot,
        )

        assert success is True

        # Verify sysroot structure
        assert (temp_output_dir / "usr" / "bin").exists()
        assert (temp_output_dir / "usr" / "lib").exists() or (
            temp_output_dir / "usr" / "lib64"
        ).exists()
        assert (temp_output_dir / "etc").exists()
        assert (temp_output_dir / "var").exists()

        # Check for debootstrap marker files
        assert (temp_output_dir / "debootstrap").exists()

    def test_sysroot_with_deb_extraction(self, temp_output_dir, mock_deb_package):
        """Test creating sysroot and extracting a .deb package."""
        if not sysroot_maker.is_command_available("ar"):
            pytest.skip("ar command not available")

        # Create basic directory structure
        (temp_output_dir / "usr" / "bin").mkdir(parents=True)

        # Extract the mock deb
        result = sysroot_maker.extract_deb_package(
            str(mock_deb_package),
            str(temp_output_dir),
            verbose=True,
        )

        assert result is True

        # Verify extraction
        extracted_file = temp_output_dir / "usr" / "bin" / "test-binary"
        assert extracted_file.exists()


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_package_list_from_example_file(self):
        """Test reading the example packages file if it exists."""
        example_file = Path(__file__).parent.parent / "example-packages.txt"

        if example_file.exists():
            packages = sysroot_maker.read_package_list(str(example_file))
            assert len(packages) > 0
            assert all(isinstance(p, str) for p in packages)
            # Should not contain comments
            assert all(not p.startswith("#") for p in packages)

    def test_initramfs_packages_defined(self):
        """Test that INITRAMFS_PACKAGES is properly defined."""
        assert hasattr(sysroot_maker, "INITRAMFS_PACKAGES")
        assert len(sysroot_maker.INITRAMFS_PACKAGES) > 0
        assert "busybox-static" in sysroot_maker.INITRAMFS_PACKAGES
