#!/usr/bin/env python3

import os
from tools.balancer import Balancer

class TestBalance(object):

    def test_balance_already_balanced_does_nothing(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {"/disk0": (100, 200, 100), "/disk1": (100, 200, 100)}.get)
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_file("/disk0/test0", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        fs.create_file("/disk1/test1", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        balancer = Balancer(["/disk0", "/disk1"])
        balancer.balance()
        assert os.path.exists("/disk0/test0")
        assert not os.path.exists("/disk0/test1")
        assert os.path.exists("/disk1/test1")
        assert not os.path.exists("/disk1/test0")


    def test_balance_moves_single_file(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {"/disk0": (0, 200, 200), "/disk1": (200, 200, 0)}.get)
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_file("/disk0/test0", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        fs.create_file("/disk0/test1", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        balancer = Balancer(["/disk0", "/disk1"])
        balancer.balance()
        assert os.path.exists("/disk0/test0")
        assert not os.path.exists("/disk0/test1")
        assert os.path.exists("/disk1/test1")

    def test_balance_moves_biggest_files_first(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {"/disk0": (200, 200, 0), "/disk1": (100, 200, 100)}.get)
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_file("/disk1/test0", contents='a' * 50, encoding='UTF-8')  # 50 bytes
        for idx in range(1, 6):  # 50 bytes
            fs.create_file(f"/disk1/test{idx}", contents='a' * 10, encoding='UTF-8')  # 10 bytes

        balancer = Balancer(["/disk0", "/disk1"])
        balancer.balance()
        assert os.path.exists("/disk0/test0")

        for idx in range(1, 6):
            assert os.path.exists(f"/disk1/test{idx}")

    def test_balance_moves_biggest_dir_first(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {"/disk0": (200, 200, 0), "/disk1": (100, 200, 100)}.get)
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_file("/disk1/dir/test0", contents='a' * 50, encoding='UTF-8')  # 50 bytes
        for idx in range(1, 6):  # 50 bytes
            fs.create_file(f"/disk1/test{idx}", contents='a' * 10, encoding='UTF-8')  # 10 bytes

        balancer = Balancer(["/disk0", "/disk1"])
        balancer.balance()
        assert os.path.exists("/disk0/dir/test0")

        for idx in range(1, 6):
            assert os.path.exists(f"/disk1/test{idx}")

    def test_balances_most_overloaded_sources_first(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {
            "/disk0": (200, 200, 0),
            "/disk1": (100, 200, 100),
            "/disk2": (100, 200, 100),
            "/disk3": (0, 200, 200)
        }.get)

        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.add_mount_point("/disk2")
        fs.create_file("/disk1/test0", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        fs.create_file("/disk2/test1", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        fs.create_file("/disk3/test2", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        fs.create_file("/disk3/test3", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        balancer = Balancer(["/disk0", "/disk1", "/disk2", "/disk3"])
        balancer.balance()
        assert os.path.exists("/disk0/test3")
        assert os.path.exists("/disk1/test0")
        assert os.path.exists("/disk2/test1")
        assert os.path.exists("/disk3/test2")

    def test_wont_overfil_source(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {"/disk0": (0, 1000, 1000), "/disk1": (200, 200, 0)}.get)
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")

        for idx in range(0, 4):
            fs.create_file(f"/disk0/test{idx}", contents='a' * 250, encoding='UTF-8')  # 250 bytes

        balancer = Balancer(["/disk0", "/disk1"])
        balancer.balance()

        for idx in range(0, 4):
            assert os.path.exists(f"/disk0/test{idx}")
            assert not os.path.exists(f"/disk1/test{idx}")

    def test_wont_deplete_source(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {"/disk0": (100, 200, 100), "/disk1": (200, 200, 0)}.get)
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_file("/disk0/test0", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        balancer = Balancer(["/disk0", "/disk1"])
        balancer.balance()
        assert os.path.exists("/disk0/test0")
        assert not os.path.exists("/disk1/test0")

    def test_dry_run_wont_move_files(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {"/disk0": (0, 200, 200), "/disk1": (200, 200, 0)}.get)
        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.create_file("/disk0/test0", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        fs.create_file("/disk0/test1", contents='a' * 100, encoding='UTF-8')  # 100 bytes
        balancer = Balancer(["/disk0", "/disk1"])
        balancer.balance(True)
        assert os.path.exists("/disk0/test0")
        assert os.path.exists("/disk0/test1")
        assert not os.path.exists("/disk1/test0")
        assert not os.path.exists("/disk1/test1")

    def test_file_will_only_be_balanced_once(self, fs, monkeypatch):
        monkeypatch.setattr(Balancer, "_get_source_usage_stats", {
            "/disk0": (100, 200, 100),
            "/disk1": (200, 200, 0),
            "/disk2": (200, 200, 0)
        }.get)

        fs.add_mount_point("/disk0")
        fs.add_mount_point("/disk1")
        fs.add_mount_point("/disk2")
        for idx in range(0, 5):  # 100 bytes
            fs.create_file(f"/disk0/test{idx}", contents='a' * 20, encoding='UTF-8')  # 20 bytes

        balancer = Balancer(["/disk0", "/disk1", "/disk2"])
        balancer.balance()
        assert os.path.exists("/disk2/test4")
        assert os.path.exists("/disk1/test3")
        assert os.path.exists("/disk0/test2")
        assert os.path.exists("/disk0/test1")
        assert os.path.exists("/disk0/test0")
