# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 sysroot-maker contributors
"""Unit tests for sysroot_maker utility functions (mocked)."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

import sysroot_maker


@pytest.mark.unit
class TestMirrorSelection:
    """Test mirror URL selection based on architecture."""
    
    def test_arm64_uses_ports_mirror(self):
        assert sysroot_maker.get_mirror_for_arch("arm64") == "http://ports.ubuntu.com/ubuntu-ports"
    
    def test_armhf_uses_ports_mirror(self):
        assert sysroot_maker.get_mirror_for_arch("armhf") == "http://ports.ubuntu.com/ubuntu-ports"
    
    def test_ppc64el_uses_ports_mirror(self):
        assert sysroot_maker.get_mirror_for_arch("ppc64el") == "http://ports.ubuntu.com/ubuntu-ports"
    
    def test_s390x_uses_ports_mirror(self):
        assert sysroot_maker.get_mirror_for_arch("s390x") == "http://ports.ubuntu.com/ubuntu-ports"
    
    def test_riscv64_uses_ports_mirror(self):
        assert sysroot_maker.get_mirror_for_arch("riscv64") == "http://ports.ubuntu.com/ubuntu-ports"
    
    def test_amd64_uses_main_archive(self):
        assert sysroot_maker.get_mirror_for_arch("amd64") == "http://archive.ubuntu.com/ubuntu"
    
    def test_i386_uses_main_archive(self):
        assert sysroot_maker.get_mirror_for_arch("i386") == "http://archive.ubuntu.com/ubuntu"
    
    def test_unknown_arch_uses_main_archive(self):
        assert sysroot_maker.get_mirror_for_arch("unknown") == "http://archive.ubuntu.com/ubuntu"


@pytest.mark.unit
class TestCommandAvailability:
    """Test command availability checking."""
    
    def test_command_available_when_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")
        assert sysroot_maker.is_command_available("debootstrap") is True
    
    def test_command_not_available_when_not_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        assert sysroot_maker.is_command_available("debootstrap") is False
    
    def test_command_availability_for_ar(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/ar" if cmd == "ar" else None)
        assert sysroot_maker.is_command_available("ar") is True
        assert sysroot_maker.is_command_available("missing") is False


@pytest.mark.unit
class TestRootCheck:
    """Test root privilege checking."""
    
    def test_is_root_when_euid_is_zero(self, monkeypatch):
        monkeypatch.setattr("os.geteuid", lambda: 0)
        assert sysroot_maker.is_root() is True
    
    def test_is_not_root_when_euid_is_nonzero(self, monkeypatch):
        monkeypatch.setattr("os.geteuid", lambda: 1000)
        assert sysroot_maker.is_root() is False


@pytest.mark.unit
class TestPackageListReading:
    """Test reading package lists from files."""
    
    def test_read_package_list_basic(self, sample_package_list):
        packages = sysroot_maker.read_package_list(str(sample_package_list))
        assert packages == ["busybox-static", "klibc-utils", "initramfs-tools-core"]
    
    def test_read_package_list_ignores_comments(self, sample_package_list):
        packages = sysroot_maker.read_package_list(str(sample_package_list))
        assert len([p for p in packages if p.startswith("#")]) == 0
    
    def test_read_package_list_empty_file(self, empty_package_list):
        packages = sysroot_maker.read_package_list(str(empty_package_list))
        assert packages == []
    
    def test_read_package_list_file_not_found(self):
        with pytest.raises(SystemExit) as exc_info:
            sysroot_maker.read_package_list("/nonexistent/file.txt")
        assert exc_info.value.code == 1
    
    def test_read_package_list_strips_whitespace(self, tmp_path):
        pkg_file = tmp_path / "whitespace.txt"
        pkg_file.write_text("  package1  \n\npackage2\n  \n")
        packages = sysroot_maker.read_package_list(str(pkg_file))
        assert packages == ["package1", "package2"]


@pytest.mark.unit
class TestDiskSpaceCheck:
    """Test disk space checking."""
    
    def test_check_disk_space_sufficient(self, monkeypatch):
        mock_statvfs = Mock()
        mock_statvfs.f_bavail = 1000000  # blocks
        mock_statvfs.f_frsize = 4096  # bytes per block
        # Total: ~4GB available
        
        monkeypatch.setattr("os.statvfs", lambda path: mock_statvfs)
        assert sysroot_maker.check_disk_space("/tmp", required_gb=2.0) is True
    
    def test_check_disk_space_insufficient(self, monkeypatch):
        mock_statvfs = Mock()
        mock_statvfs.f_bavail = 100000  # blocks
        mock_statvfs.f_frsize = 4096  # bytes per block
        # Total: ~400MB available
        
        monkeypatch.setattr("os.statvfs", lambda path: mock_statvfs)
        assert sysroot_maker.check_disk_space("/tmp", required_gb=2.0) is False
    
    def test_check_disk_space_os_error(self, monkeypatch):
        monkeypatch.setattr("os.statvfs", Mock(side_effect=OSError("Permission denied")))
        # Should return True (assume OK) when check fails
        assert sysroot_maker.check_disk_space("/tmp") is True


@pytest.mark.unit
class TestDebArchitectureValidation:
    """Test .deb package architecture validation."""
    
    @patch("subprocess.run")
    @patch("tempfile.TemporaryDirectory")
    @patch("pathlib.Path.glob")
    def test_validate_correct_architecture(self, mock_glob, mock_tmpdir, mock_run):
        # Setup mocks
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = [Path("/tmp/test/control.tar.gz")]
        
        # Mock ar extraction
        mock_run.side_effect = [
            Mock(returncode=0),  # ar extraction
            Mock(returncode=0, stdout="Architecture: arm64\n"),  # tar extraction
        ]
        
        result = sysroot_maker.validate_deb_architecture("/path/to/package.deb", "arm64")
        assert result is True
    
    @patch("subprocess.run")
    @patch("tempfile.TemporaryDirectory")
    @patch("pathlib.Path.glob")
    def test_validate_architecture_all_is_valid(self, mock_glob, mock_tmpdir, mock_run):
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = [Path("/tmp/test/control.tar.gz")]
        
        mock_run.side_effect = [
            Mock(returncode=0),
            Mock(returncode=0, stdout="Architecture: all\n"),
        ]
        
        result = sysroot_maker.validate_deb_architecture("/path/to/package.deb", "arm64")
        assert result is True
    
    @patch("subprocess.run")
    @patch("tempfile.TemporaryDirectory")
    @patch("pathlib.Path.glob")
    def test_validate_wrong_architecture(self, mock_glob, mock_tmpdir, mock_run):
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = [Path("/tmp/test/control.tar.gz")]
        
        mock_run.side_effect = [
            Mock(returncode=0),
            Mock(returncode=0, stdout="Architecture: amd64\n"),
        ]
        
        result = sysroot_maker.validate_deb_architecture("/path/to/package.deb", "arm64")
        assert result is False


@pytest.mark.unit
class TestDownloadKernelPackage:
    """Test kernel package download URL construction."""
    
    @patch("urllib.request.urlretrieve")
    def test_download_kernel_package_success(self, mock_urlretrieve, tmp_path):
        mock_urlretrieve.return_value = None
        
        result = sysroot_maker.download_kernel_package(
            package_name="linux-image-6.8.0-51-generic",
            version="6.8.0-51.52",
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            target_dir=str(tmp_path),
            verbose=False,
        )
        
        assert result is not None
        assert "linux-image-6.8.0-51-generic_6.8.0-51.52_arm64.deb" in result
        mock_urlretrieve.assert_called_once()
    
    @patch("urllib.request.urlretrieve")
    def test_download_kernel_package_failure(self, mock_urlretrieve, tmp_path):
        mock_urlretrieve.side_effect = Exception("Network error")
        
        result = sysroot_maker.download_kernel_package(
            package_name="linux-image-test",
            version="1.0.0",
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            target_dir=str(tmp_path),
            verbose=False,
        )
        
        assert result is None


@pytest.mark.unit
class TestRunDebootstrap:
    """Test debootstrap command construction and execution."""
    
    @patch("subprocess.run")
    def test_run_debootstrap_basic(self, mock_run, tmp_path):
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
        
        result = sysroot_maker.run_debootstrap(
            output_dir=str(tmp_path),
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=[],
            verbose=False,
            use_fakeroot=False,
        )
        
        assert result is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "debootstrap" in cmd
        assert "--foreign" in cmd
        assert "--arch=arm64" in cmd
        assert "noble" in cmd
    
    @patch("subprocess.run")
    def test_run_debootstrap_with_fakeroot(self, mock_run, tmp_path):
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
        
        result = sysroot_maker.run_debootstrap(
            output_dir=str(tmp_path),
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=[],
            verbose=False,
            use_fakeroot=True,
        )
        
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "fakeroot"
        assert "debootstrap" in cmd
    
    @patch("subprocess.run")
    def test_run_debootstrap_with_packages(self, mock_run, tmp_path):
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
        
        result = sysroot_maker.run_debootstrap(
            output_dir=str(tmp_path),
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=["busybox-static", "klibc-utils"],
            verbose=False,
            use_fakeroot=False,
        )
        
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert any("--include=busybox-static,klibc-utils" in arg for arg in cmd)
    
    @patch("subprocess.run")
    def test_run_debootstrap_failure(self, mock_run, tmp_path):
        mock_run.return_value = Mock(returncode=1, stderr="Error occurred", stdout="")
        
        result = sysroot_maker.run_debootstrap(
            output_dir=str(tmp_path),
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=[],
            verbose=False,
            use_fakeroot=False,
        )
        
        assert result is False
    
    @patch("subprocess.run")
    def test_run_debootstrap_subprocess_error(self, mock_run, tmp_path):
        """Test handling of subprocess errors."""
        mock_run.side_effect = subprocess.SubprocessError("Command failed")
        
        result = sysroot_maker.run_debootstrap(
            output_dir=str(tmp_path),
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=[],
            verbose=False,
            use_fakeroot=False,
        )
        
        assert result is False
    
    @patch("subprocess.run")
    def test_run_debootstrap_verbose_mode(self, mock_run, tmp_path):
        """Test verbose output mode."""
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
        
        result = sysroot_maker.run_debootstrap(
            output_dir=str(tmp_path),
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            packages=["test-pkg"],
            verbose=True,
            use_fakeroot=True,
        )
        
        assert result is True
        # In verbose mode, stdout and stderr should not be captured
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("stdout") is None
        assert call_kwargs.get("stderr") is None


@pytest.mark.unit
class TestExtractDebPackage:
    """Test .deb package extraction with mocking."""
    
    @patch("subprocess.run")
    @patch("pathlib.Path.glob")
    @patch("tempfile.TemporaryDirectory")
    def test_extract_deb_success(self, mock_tmpdir, mock_glob, mock_run, tmp_path):
        """Test successful .deb extraction."""
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = [Path("/tmp/test/data.tar.gz")]
        mock_run.return_value = Mock(returncode=0)
        
        # Create a fake deb file
        deb_path = tmp_path / "test.deb"
        deb_path.write_text("fake deb")
        
        result = sysroot_maker.extract_deb_package(
            str(deb_path), str(tmp_path), verbose=False
        )
        
        assert result is True
        # Should call ar and tar
        assert mock_run.call_count == 2
    
    @patch("subprocess.run")
    @patch("pathlib.Path.glob")
    @patch("tempfile.TemporaryDirectory")
    def test_extract_deb_ar_extraction_fails(self, mock_tmpdir, mock_glob, mock_run, tmp_path):
        """Test ar extraction failure."""
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_run.side_effect = subprocess.CalledProcessError(1, "ar")
        
        deb_path = tmp_path / "test.deb"
        deb_path.write_text("fake deb")
        
        result = sysroot_maker.extract_deb_package(
            str(deb_path), str(tmp_path), verbose=False
        )
        
        assert result is False
    
    @patch("subprocess.run")
    @patch("pathlib.Path.glob")
    @patch("tempfile.TemporaryDirectory")
    def test_extract_deb_no_data_archive(self, mock_tmpdir, mock_glob, mock_run, tmp_path):
        """Test missing data archive."""
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = []  # No data archive found
        mock_run.return_value = Mock(returncode=0)
        
        deb_path = tmp_path / "test.deb"
        deb_path.write_text("fake deb")
        
        result = sysroot_maker.extract_deb_package(
            str(deb_path), str(tmp_path), verbose=False
        )
        
        assert result is False
    
    @patch("subprocess.run")
    @patch("pathlib.Path.glob")
    @patch("tempfile.TemporaryDirectory")
    def test_extract_deb_tar_extraction_fails(self, mock_tmpdir, mock_glob, mock_run, tmp_path):
        """Test tar extraction failure."""
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = [Path("/tmp/test/data.tar.gz")]
        
        # First call (ar) succeeds, second call (tar) fails
        mock_run.side_effect = [
            Mock(returncode=0),
            subprocess.CalledProcessError(1, "tar"),
        ]
        
        deb_path = tmp_path / "test.deb"
        deb_path.write_text("fake deb")
        
        result = sysroot_maker.extract_deb_package(
            str(deb_path), str(tmp_path), verbose=False
        )
        
        assert result is False
    
    def test_extract_deb_file_not_found(self, tmp_path):
        """Test extraction of non-existent file."""
        result = sysroot_maker.extract_deb_package(
            "/nonexistent/file.deb", str(tmp_path), verbose=False
        )
        
        assert result is False
    
    @patch("subprocess.run")
    @patch("pathlib.Path.glob")
    @patch("tempfile.TemporaryDirectory")
    def test_extract_deb_verbose_mode(self, mock_tmpdir, mock_glob, mock_run, tmp_path):
        """Test verbose mode output."""
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = [Path("/tmp/test/data.tar.gz")]
        mock_run.return_value = Mock(returncode=0)
        
        deb_path = tmp_path / "test.deb"
        deb_path.write_text("fake deb")
        
        result = sysroot_maker.extract_deb_package(
            str(deb_path), str(tmp_path), verbose=True
        )
        
        assert result is True


@pytest.mark.unit
class TestValidateDebArchitectureExtended:
    """Extended tests for .deb architecture validation."""
    
    @patch("subprocess.run")
    @patch("tempfile.TemporaryDirectory")
    @patch("pathlib.Path.glob")
    def test_validate_no_control_archive(self, mock_glob, mock_tmpdir, mock_run):
        """Test when control archive is missing."""
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = []  # No control archive
        mock_run.return_value = Mock(returncode=0)
        
        result = sysroot_maker.validate_deb_architecture("/path/to/package.deb", "arm64", verbose=True)
        assert result is True  # Should assume valid
    
    @patch("subprocess.run")
    @patch("tempfile.TemporaryDirectory")
    @patch("pathlib.Path.glob")
    def test_validate_subprocess_error(self, mock_glob, mock_tmpdir, mock_run):
        """Test subprocess error handling."""
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = [Path("/tmp/test/control.tar.gz")]
        mock_run.side_effect = subprocess.CalledProcessError(1, "ar")
        
        result = sysroot_maker.validate_deb_architecture("/path/to/package.deb", "arm64", verbose=True)
        assert result is True  # Should assume valid on error
    
    @patch("subprocess.run")
    @patch("tempfile.TemporaryDirectory")
    @patch("pathlib.Path.glob")
    def test_validate_no_architecture_field(self, mock_glob, mock_tmpdir, mock_run):
        """Test when Architecture field is missing."""
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"
        mock_glob.return_value = [Path("/tmp/test/control.tar.gz")]
        
        mock_run.side_effect = [
            Mock(returncode=0),
            Mock(returncode=0, stdout="Package: test\nVersion: 1.0\n"),  # No Architecture field
        ]
        
        result = sysroot_maker.validate_deb_architecture("/path/to/package.deb", "arm64", verbose=True)
        assert result is True  # Should assume valid


@pytest.mark.unit
class TestDownloadKernelPackageExtended:
    """Extended tests for kernel package downloads."""
    
    @patch("urllib.request.urlretrieve")
    def test_download_constructs_correct_url(self, mock_urlretrieve, tmp_path):
        """Test URL construction."""
        mock_urlretrieve.return_value = None
        
        sysroot_maker.download_kernel_package(
            package_name="linux-image-6.8.0-51-generic",
            version="6.8.0-51.52",
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            target_dir=str(tmp_path),
            verbose=True,
        )
        
        call_args = mock_urlretrieve.call_args[0]
        url = call_args[0]
        assert "http://ports.ubuntu.com/ubuntu-ports/pool/main/l/linux/" in url
        assert "linux-image-6.8.0-51-generic_6.8.0-51.52_arm64.deb" in url
    
    @patch("urllib.request.urlretrieve")
    def test_download_returns_correct_path(self, mock_urlretrieve, tmp_path):
        """Test returned path."""
        mock_urlretrieve.return_value = None
        
        result = sysroot_maker.download_kernel_package(
            package_name="linux-modules-test",
            version="1.0.0",
            arch="amd64",
            release="jammy",
            mirror="http://archive.ubuntu.com/ubuntu",
            target_dir=str(tmp_path),
            verbose=False,
        )
        
        assert result is not None
        assert tmp_path.name in result
        assert "linux-modules-test_1.0.0_amd64.deb" in result
    
    @patch("urllib.request.urlretrieve")
    def test_download_ioerror(self, mock_urlretrieve, tmp_path):
        """Test I/O error handling."""
        mock_urlretrieve.side_effect = IOError("Network error")
        
        result = sysroot_maker.download_kernel_package(
            package_name="linux-image-test",
            version="1.0.0",
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            target_dir=str(tmp_path),
            verbose=False,
        )
        
        assert result is None
    
    @patch("urllib.request.urlretrieve")
    def test_download_generic_exception(self, mock_urlretrieve, tmp_path):
        """Test generic exception handling."""
        mock_urlretrieve.side_effect = RuntimeError("Unexpected error")
        
        result = sysroot_maker.download_kernel_package(
            package_name="linux-image-test",
            version="1.0.0",
            arch="arm64",
            release="noble",
            mirror="http://ports.ubuntu.com/ubuntu-ports",
            target_dir=str(tmp_path),
            verbose=True,
        )
        
        assert result is None
