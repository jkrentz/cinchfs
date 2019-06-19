#!/usr/bin/env python

import pytest
import os
from cinchfs import cinchfs, DuplicatePathException


class TestStartup(object):

    def test_constructor_empty_filesystem_succeeds(self, fs):
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        cfs = cinchfs(["/disk0", "/disk1"])
        pass # no exception

    def test_constructor_no_collisions_succeeds(self, fs):
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_file("/disk0/dir0/test")
        fs.create_file("/disk1/dir1/test")
        cfs = cinchfs(["/disk0", "/disk1"])
        pass # no exception

    def test_constructor_file_collision_fails(self, fs):
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_file("/disk0/test")
        fs.create_file("/disk1/test")
        with pytest.raises(DuplicatePathException) as e:
            assert cinchfs(["/disk0", "/disk1"])

    def test_constructor_dir_collision_fails(self, fs):
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_dir("/disk0/dir")
        fs.create_dir("/disk1/dir")
        with pytest.raises(DuplicatePathException) as e:
            assert cinchfs(["/disk0", "/disk1"])


class TestFullPath(object):

    def test_fullpath_single_empty_source_root(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50 }.get) 
        fs.add_mount_point("/disk0")
        cfs = cinchfs(["/disk0"])
        assert cfs._full_path("/") == "/disk0/"

    def test_fullpath_multiple_empty_sources_root_uses_first_source(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50, "/disk1": 100 }.get)
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/") == "/disk0/"

    def test_fullpath_single_empty_source_new_file(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50 }.get) 
        fs.add_mount_point("/disk0")
        cfs = cinchfs(["/disk0"])
        assert cfs._full_path("/test") == "/disk0/test"
    
    def test_fullpath_single_empty_source_new_file_in_directory(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50 }.get) 
        fs.add_mount_point("/disk0")
        cfs = cinchfs(["/disk0"])
        assert cfs._full_path("/dir/test") == "/disk0/dir/test"

    def test_fullpath_single_empty_source_new_dir(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50 }.get) 
        fs.add_mount_point("/disk0")
        cfs = cinchfs(["/disk0"])
        assert cfs._full_path("/dir/") == "/disk0/dir/"

    def test_fullpath_multiple_empty_sources_new_file_uses_first_source(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50, "/disk1": 50 }.get) 
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/test") == "/disk0/test"
    
    def test_fullpath_multiple_empty_sources_new_file_in_directory_uses_first_source(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50, "/disk1": 50 }.get) 
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/dir/test") == "/disk0/dir/test"
    
    def test_fullpath_multiple_empty_sources_new_dir_uses_first_source(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50, "/disk1": 50 }.get) 
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/dir/") == "/disk0/dir/"
    
    def test_fullpath_single_source_file_exists(self, fs):
        fs.create_file("/disk0/test")
        cfs = cinchfs(["/disk0"])
        assert cfs._full_path("/test") == "/disk0/test"

    def test_fullpath_single_source_file_exists_in_directory(self, fs):
        fs.create_file("/disk0/dir/test")
        cfs = cinchfs(["/disk0"])
        assert cfs._full_path("/dir/test") == "/disk0/dir/test"

    def test_fullpath_single_source_directory_exists(self, fs):
        fs.create_dir("/disk0/dir/")
        cfs = cinchfs(["/disk0"])
        assert cfs._full_path("/dir/") == "/disk0/dir/"

    def test_fullpath_multiple_source_file_exists_uses_existing_file(self, fs):
        fs.create_dir("/disk0")
        fs.create_file("/disk1/test")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/test") == "/disk1/test"
    
    def test_fullpath_multiple_source_file_exists_in_directory_uses_existing_fil(self, fs):
        fs.create_dir("/disk0")
        fs.create_file("/disk1/dir/test")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/dir/test") == "/disk1/dir/test"
    
    def test_fullpath_multiple_source_directory_exists_uses_existing_directory(self, fs):
        fs.create_dir("/disk0")
        fs.create_dir("/disk1/dir/")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/dir/") == "/disk1/dir/"

    def test_fullpath_multiple_sources_new_file_uses_most_free_space_source(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50, "/disk1": 100 }.get) 
        fs.add_mount_point("/disk0", 50)
        fs.add_mount_point("/disk1", 100)
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/test") == "/disk1/test"

    def test_fullpath_multiple_empty_sources_new_file_in_directory_uses_the_existing_directory_source(self, fs, monkeypatch):
        # disk1 has more free space, but prefer the existing dir on disk0
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50, "/disk1": 100 }.get) 
        fs.add_mount_point("/disk0", 50)
        fs.add_mount_point("/disk1", 100)
        fs.create_dir("/disk0/dir")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/dir/test") == "/disk0/dir/test"

    def test_fullpath_multiple_empty_sources_new_file_in_subdirectory_uses_the_existing_base_directory_source(self, fs, monkeypatch):
        # disk1 has more free space, but prefer the existing base dir on disk0
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50, "/disk1": 100 }.get) 
        fs.add_mount_point("/disk0", 50)
        fs.add_mount_point("/disk1", 100)
        fs.create_dir("/disk0/basedir/dir")
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/basedir/dir/test") == "/disk0/basedir/dir/test"

    def test_fullpath_multiple_empty_sources_new_dir_uses_most_free_space_source(self, fs, monkeypatch):
        monkeypatch.setattr(cinchfs, "_get_free_blocks", { "/disk0": 50, "/disk1": 100 }.get) 
        fs.add_mount_point("/disk0", 50)
        fs.add_mount_point("/disk1", 100)
        cfs = cinchfs(["/disk0", "/disk1"])
        assert cfs._full_path("/dir/") == "/disk1/dir/"

