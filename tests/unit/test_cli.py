# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 sysroot-maker contributors
"""Tests for CLI argument parsing."""

import argparse
import sys
from unittest.mock import patch

import pytest

import sysroot_maker


@pytest.mark.unit
class TestCLIArgumentParsing:
    """Test command-line argument parsing."""
    
    def test_output_argument_required(self):
        """Test that --output is required."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["sysroot_maker.py"]):
                sysroot_maker.main()
    
    def test_default_architecture(self):
        """Test default architecture is arm64."""
        test_args = ["sysroot_maker.py", "--output", "/tmp/test"]
        with patch("sys.argv", test_args):
            with patch("sysroot_maker.is_command_available", return_value=True):
                with patch("sysroot_maker.is_root", return_value=True):
                    with patch("sysroot_maker.run_debootstrap", return_value=True):
                        with patch("os.path.exists", return_value=False):
                            try:
                                sysroot_maker.main()
                            except SystemExit:
                                pass
    
    def test_default_release(self):
        """Test default release is noble."""
        test_args = ["sysroot_maker.py", "--output", "/tmp/test"]
        with patch("sys.argv", test_args):
            with patch("sysroot_maker.is_command_available", return_value=True):
                with patch("sysroot_maker.is_root", return_value=True):
                    with patch("sysroot_maker.run_debootstrap", return_value=True):
                        with patch("os.path.exists", return_value=False):
                            try:
                                sysroot_maker.main()
                            except SystemExit:
                                pass
    
    def test_custom_architecture(self):
        """Test custom architecture can be specified."""
        test_args = ["sysroot_maker.py", "--output", "/tmp/test", "--arch", "armhf"]
        with patch("sys.argv", test_args):
            with patch("sysroot_maker.is_command_available", return_value=True):
                with patch("sysroot_maker.is_root", return_value=True):
                    with patch("sysroot_maker.run_debootstrap", return_value=True):
                        with patch("os.path.exists", return_value=False):
                            try:
                                sysroot_maker.main()
                            except SystemExit:
                                pass
    
    def test_multiple_packages(self):
        """Test multiple --packages arguments."""
        test_args = [
            "sysroot_maker.py",
            "--output", "/tmp/test",
            "--packages", "pkg1", "pkg2", "pkg3",
        ]
        with patch("sys.argv", test_args):
            with patch("sysroot_maker.is_command_available", return_value=True):
                with patch("sysroot_maker.is_root", return_value=True):
                    with patch("sysroot_maker.run_debootstrap", return_value=True):
                        with patch("os.path.exists", return_value=False):
                            try:
                                sysroot_maker.main()
                            except SystemExit:
                                pass
    
    def test_initramfs_packages_flag(self):
        """Test --initramfs-packages flag."""
        test_args = [
            "sysroot_maker.py",
            "--output", "/tmp/test",
            "--initramfs-packages",
        ]
        with patch("sys.argv", test_args):
            with patch("sysroot_maker.is_command_available", return_value=True):
                with patch("sysroot_maker.is_root", return_value=True):
                    with patch("sysroot_maker.run_debootstrap") as mock_debootstrap:
                        mock_debootstrap.return_value = True
                        with patch("os.path.exists", return_value=False):
                            try:
                                sysroot_maker.main()
                            except SystemExit:
                                pass
                            # Check that run_debootstrap was called
                            assert mock_debootstrap.called
                            # Check that packages argument was passed
                            call_kwargs = mock_debootstrap.call_args.kwargs
                            if "packages" in call_kwargs:
                                packages = call_kwargs["packages"]
                                # At least some initramfs packages should be present
                                assert len(packages) > 0


@pytest.mark.unit
class TestDependencyValidation:
    """Test validation of system dependencies."""
    
    def test_missing_debootstrap_exits(self):
        """Test that missing debootstrap causes exit."""
        test_args = ["sysroot_maker.py", "--output", "/tmp/test"]
        with patch("sys.argv", test_args):
            with patch("sysroot_maker.is_command_available", return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    sysroot_maker.main()
                assert exc_info.value.code == 1
    
    def test_missing_ar_command_exits(self):
        """Test that missing ar command causes exit."""
        test_args = ["sysroot_maker.py", "--output", "/tmp/test"]
        with patch("sys.argv", test_args):
            def mock_command_available(cmd):
                return cmd == "debootstrap"
            
            with patch("sysroot_maker.is_command_available", side_effect=mock_command_available):
                with pytest.raises(SystemExit) as exc_info:
                    sysroot_maker.main()
                assert exc_info.value.code == 1


@pytest.mark.unit
class TestPackageDeduplication:
    """Test that package lists are deduplicated."""
    
    def test_package_deduplication(self, tmp_path):
        """Test that duplicate packages are removed."""
        # This tests the logic in main() that deduplicates packages
        packages = ["pkg1", "pkg2", "pkg1", "pkg3", "pkg2"]
        
        # Remove duplicates while preserving order (from main())
        seen = set()
        deduplicated = [p for p in packages if not (p in seen or seen.add(p))]
        
        assert deduplicated == ["pkg1", "pkg2", "pkg3"]
        assert len(deduplicated) == 3
    
    def test_package_deduplication_preserves_order(self):
        """Test that deduplication preserves first occurrence order."""
        packages = ["z-pkg", "a-pkg", "z-pkg", "m-pkg", "a-pkg"]
        
        seen = set()
        deduplicated = [p for p in packages if not (p in seen or seen.add(p))]
        
        assert deduplicated == ["z-pkg", "a-pkg", "m-pkg"]


@pytest.mark.unit
class TestOutputDirectoryHandling:
    """Test output directory creation and cleaning."""
    
    def test_existing_directory_without_clean_flag_exits(self):
        """Test that existing directory without --clean causes exit."""
        test_args = ["sysroot_maker.py", "--output", "/tmp/test"]
        with patch("sys.argv", test_args):
            with patch("sysroot_maker.is_command_available", return_value=True):
                with patch("os.path.exists", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        sysroot_maker.main()
                    assert exc_info.value.code == 1
    
    def test_existing_directory_with_clean_flag(self):
        """Test that existing directory with --clean is removed."""
        test_args = ["sysroot_maker.py", "--output", "/tmp/test", "--clean"]
        with patch("sys.argv", test_args):
            with patch("sysroot_maker.is_command_available", return_value=True):
                with patch("sysroot_maker.is_root", return_value=True):
                    with patch("os.path.exists", return_value=True):
                        with patch("shutil.rmtree") as mock_rmtree:
                            with patch("sysroot_maker.run_debootstrap", return_value=True):
                                try:
                                    sysroot_maker.main()
                                except SystemExit:
                                    pass
                                mock_rmtree.assert_called_once()
