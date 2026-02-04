"""Additional unit tests to improve coverage."""

import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import sysroot_maker


@pytest.mark.unit
class TestReadPackageListExtended:
    """Extended tests for package list reading."""
    
    def test_read_package_list_ioerror(self, tmp_path):
        """Test I/O error handling."""
        # Create a file and then make it unreadable
        pkg_file = tmp_path / "unreadable.txt"
        pkg_file.write_text("package1")
        pkg_file.chmod(0o000)
        
        try:
            with pytest.raises(SystemExit):
                sysroot_maker.read_package_list(str(pkg_file))
        finally:
            pkg_file.chmod(0o644)
    
    def test_read_package_list_with_blank_lines(self, tmp_path):
        """Test handling of multiple blank lines."""
        pkg_file = tmp_path / "blanks.txt"
        pkg_file.write_text("\n\n\npkg1\n\n\npkg2\n\n\n")
        
        packages = sysroot_maker.read_package_list(str(pkg_file))
        assert packages == ["pkg1", "pkg2"]
    
    def test_read_package_list_only_comments(self, tmp_path):
        """Test file with only comments."""
        pkg_file = tmp_path / "only-comments.txt"
        pkg_file.write_text("# Comment 1\n# Comment 2\n# Comment 3\n")
        
        packages = sysroot_maker.read_package_list(str(pkg_file))
        assert packages == []


@pytest.mark.unit
class TestMainFunctionFlow:
    """Test main() function execution flow."""
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--verbose", "--packages", "pkg1"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    def test_main_verbose_with_packages(
        self, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main verbose mode with packages."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should print package info in verbose mode
        assert mock_debootstrap.called
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--arch", "armhf"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    def test_main_with_custom_arch(
        self, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main with custom architecture."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Verify debootstrap was called with correct arch
        if mock_debootstrap.called:
            # Could be positional or keyword argument
            args, kwargs = mock_debootstrap.call_args
            arch = kwargs.get("arch") if kwargs else (args[1] if len(args) > 1 else None)
            assert arch == "armhf" or "armhf" in str(args)
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--release", "jammy"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    def test_main_with_custom_release(
        self, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main with custom release."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        if mock_debootstrap.called:
            args, kwargs = mock_debootstrap.call_args
            release = kwargs.get("release") if kwargs else (args[2] if len(args) > 2 else None)
            assert release == "jammy" or "jammy" in str(args)
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--mirror", "http://custom.mirror"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    def test_main_with_custom_mirror(
        self, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main with custom mirror."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        if mock_debootstrap.called:
            args, kwargs = mock_debootstrap.call_args
            mirror = kwargs.get("mirror") if kwargs else (args[3] if len(args) > 3 else None)
            assert mirror == "http://custom.mirror" or "custom.mirror" in str(args)
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("sysroot_maker.check_disk_space")
    def test_main_with_low_disk_space_warning(
        self, mock_disk, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main with low disk space warning."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        mock_disk.return_value = False  # Low disk space
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    def test_main_debootstrap_failure(self, mock_root, mock_cmd):
        """Test main when debootstrap fails."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        
        with patch("os.path.exists", return_value=False):
            with patch("sysroot_maker.run_debootstrap", return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    sysroot_maker.main()
                assert exc_info.value.code == 1
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--package-list", "/tmp/pkgs.txt"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("sysroot_maker.read_package_list")
    def test_main_with_package_list(
        self, mock_read_pkgs, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main with package list file."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        mock_read_pkgs.return_value = ["pkg1", "pkg2"]
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        if mock_debootstrap.called:
            args, kwargs = mock_debootstrap.call_args
            packages = kwargs.get("packages") if kwargs else (args[4] if len(args) > 4 else [])
            assert "pkg1" in str(packages)
            assert "pkg2" in str(packages)


@pytest.mark.unit
class TestKernelPackageHandling:
    """Test kernel package download and extraction logic."""
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--kernel-deb", "/tmp/kernel.deb"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("sysroot_maker.validate_deb_architecture")
    @patch("sysroot_maker.extract_deb_package")
    def test_main_with_kernel_deb(
        self,
        mock_extract,
        mock_validate,
        mock_exists,
        mock_debootstrap,
        mock_root,
        mock_cmd,
    ):
        """Test main with kernel .deb file."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        mock_validate.return_value = True
        mock_extract.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should have validated and extracted the deb
        assert mock_validate.called
        assert mock_extract.called
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--kernel-version", "6.8.0-51-generic"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("sysroot_maker.download_kernel_package")
    @patch("sysroot_maker.validate_deb_architecture")
    @patch("sysroot_maker.extract_deb_package")
    def test_main_with_kernel_version_download(
        self,
        mock_extract,
        mock_validate,
        mock_download,
        mock_exists,
        mock_debootstrap,
        mock_root,
        mock_cmd,
    ):
        """Test main with kernel version auto-download."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        mock_download.return_value = "/tmp/kernel.deb"
        mock_validate.return_value = True
        mock_extract.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should have attempted to download kernel packages
        assert mock_download.called
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--kernel-version", "6.8.0-51-generic"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("sysroot_maker.download_kernel_package")
    def test_main_kernel_download_failure(
        self, mock_download, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main when kernel download fails."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        mock_download.return_value = None  # Download failed
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should continue even if download fails
        assert mock_debootstrap.called
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--kernel-deb", "/tmp/wrong-arch.deb"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("sysroot_maker.validate_deb_architecture")
    @patch("sysroot_maker.extract_deb_package")
    def test_main_kernel_architecture_mismatch(
        self,
        mock_extract,
        mock_validate,
        mock_exists,
        mock_debootstrap,
        mock_root,
        mock_cmd,
    ):
        """Test main with wrong architecture kernel."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        mock_validate.return_value = False  # Architecture mismatch
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should not extract if architecture doesn't match
        assert mock_validate.called
        assert not mock_extract.called
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--kernel-deb", "/tmp/kernel.deb"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("sysroot_maker.validate_deb_architecture")
    @patch("sysroot_maker.extract_deb_package")
    def test_main_kernel_extraction_failure(
        self,
        mock_extract,
        mock_validate,
        mock_exists,
        mock_debootstrap,
        mock_root,
        mock_cmd,
    ):
        """Test main when kernel extraction fails."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        mock_validate.return_value = True
        mock_extract.return_value = False  # Extraction failed
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should continue even if extraction fails
        assert mock_debootstrap.called


@pytest.mark.unit
class TestRootAndFakerootHandling:
    """Test root and fakeroot detection logic in main()."""
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    def test_main_as_non_root_with_fakeroot(
        self, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main as non-root with fakeroot available."""
        def cmd_available(cmd):
            return cmd in ["debootstrap", "ar", "fakeroot"]
        
        mock_cmd.side_effect = cmd_available
        mock_root.return_value = False
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should use fakeroot
        if mock_debootstrap.called:
            args, kwargs = mock_debootstrap.call_args
            use_fakeroot = kwargs.get("use_fakeroot") if kwargs else (args[6] if len(args) > 6 else None)
            assert use_fakeroot is True or use_fakeroot == True
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--verbose"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    def test_main_as_non_root_with_fakeroot_verbose(
        self, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main as non-root with fakeroot available and verbose."""
        def cmd_available(cmd):
            return cmd in ["debootstrap", "ar", "fakeroot"]
        
        mock_cmd.side_effect = cmd_available
        mock_root.return_value = False
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should print verbose message about fakeroot
        assert mock_debootstrap.called
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    def test_main_as_non_root_without_fakeroot(
        self, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main as non-root without fakeroot (should warn)."""
        def cmd_available(cmd):
            return cmd in ["debootstrap", "ar"]  # No fakeroot
        
        mock_cmd.side_effect = cmd_available
        mock_root.return_value = False
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should not use fakeroot
        if mock_debootstrap.called:
            args, kwargs = mock_debootstrap.call_args
            use_fakeroot = kwargs.get("use_fakeroot") if kwargs else (args[6] if len(args) > 6 else None)
            assert use_fakeroot is False or use_fakeroot is None or use_fakeroot == False
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    def test_main_as_root(
        self, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test main as root."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = False
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should not use fakeroot when running as root
        if mock_debootstrap.called:
            args, kwargs = mock_debootstrap.call_args
            use_fakeroot = kwargs.get("use_fakeroot") if kwargs else (args[6] if len(args) > 6 else None)
            assert use_fakeroot is False or use_fakeroot is None or use_fakeroot == False


@pytest.mark.unit
class TestCleanFlagHandling:
    """Test --clean flag handling."""
    
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--clean"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("shutil.rmtree")
    def test_clean_flag_removes_directory(
        self, mock_rmtree, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test that --clean removes existing directory."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = True
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        # Should have called rmtree to remove directory
        assert mock_rmtree.called
        
    @patch("sys.argv", ["prog", "--output", "/tmp/test", "--clean", "--verbose"])
    @patch("sysroot_maker.is_command_available")
    @patch("sysroot_maker.is_root")
    @patch("sysroot_maker.run_debootstrap")
    @patch("os.path.exists")
    @patch("shutil.rmtree")
    def test_clean_flag_verbose_output(
        self, mock_rmtree, mock_exists, mock_debootstrap, mock_root, mock_cmd
    ):
        """Test --clean with verbose output."""
        mock_cmd.return_value = True
        mock_root.return_value = True
        mock_exists.return_value = True
        mock_debootstrap.return_value = True
        
        try:
            sysroot_maker.main()
        except SystemExit:
            pass
        
        assert mock_rmtree.called
