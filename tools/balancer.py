#!/usr/bin/env python3

import os
import argparse
import shutil
from collections import namedtuple


class BalanceSource():
    def __init__(self, path, free_bytes, total_bytes, used_bytes):
        self.path = path
        self.free_bytes = free_bytes
        self.total_bytes = total_bytes
        self.used_bytes = used_bytes

SourceFile = namedtuple('SourceFile', 'file rel size')

class Balancer():

    def __init__(self, sources):
        self.sources = sources

    def balance(self, dry_run=False):
        balance_sources = []
        for source in self.sources:
            (free_bytes, total_bytes, used_bytes) = self._get_source_usage_stats(source)
            balance_source = BalanceSource(path=source, free_bytes=free_bytes, total_bytes=total_bytes, used_bytes=used_bytes)
            balance_sources.append(balance_source)

        desired_used_bytes = sum([source.used_bytes for source in balance_sources])/len(balance_sources)
        overloaded_sources = [source for source in balance_sources if source.used_bytes > desired_used_bytes]
        overloaded_sources.sort(key=lambda x: x.used_bytes)  # most overloaded first
        underloaded_sources = [source for source in balance_sources if source not in overloaded_sources]
        underloaded_sources.sort(key=lambda x: (x.used_bytes, x.path), reverse=True)  # most underloaded first

        for originating_source in overloaded_sources:
            files = os.listdir(originating_source.path)
            balanced_files = []

            source_files = []
            for file in files:
                orig_path = os.path.join(originating_source.path, file)
                size = self._get_path_size(orig_path)
                source_file = SourceFile(file=orig_path, rel=file, size=size)
                source_files.append(source_file)

            source_files.sort(key=lambda tup: (tup[2], tup[1]), reverse=True)  # by largest size, then reverse relative path

            for destination_source in underloaded_sources:
                # filter out files that have already been balanced to other drives
                unbalanced_source_files = [f for f in source_files if f.rel not in balanced_files]
                for source_file in unbalanced_source_files:

                    # it doesn't fit on the destination
                    if destination_source.free_bytes - source_file.size < 0:
                        continue

                    # it brings too much data to the destination
                    if destination_source.used_bytes + source_file.size > desired_used_bytes:
                        continue

                    # it makes the originator store too little data
                    if originating_source.used_bytes - source_file.size < desired_used_bytes:
                        continue

                    print(f"Moving {source_file.rel} from {originating_source.path} to {destination_source.path}")
                    if not dry_run:
                        shutil.move(source_file.file, os.path.join(destination_source.path, source_file.rel))

                    balanced_files.append(source_file.rel)
                    originating_source.used_bytes = originating_source.used_bytes - source_file.size
                    originating_source.free_bytes = originating_source.free_bytes + source_file.size
                    destination_source.used_bytes = destination_source.used_bytes + source_file.size
                    destination_source.free_bytes = destination_source.free_bytes - source_file.size

    def _get_source_usage_stats(self, source):
        st = os.statvfs(source)
        free_bytes = st.f_bavail * st.f_frsize
        total_bytes = st.f_blocks * st.f_frsize
        used_bytes = (st.f_blocks - st.f_bfree) * st.f_frsize
        return free_bytes, total_bytes, used_bytes

    def _get_path_size(self, path):
        if os.path.isfile(path):
            return os.path.getsize(path)

        # traverse dir and sum file sizes
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size
            

def main(sources, dry_run):
    balancer = Balancer(sources)
    balancer.balance(dry_run)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The Cinch Filesystem Balancer')
    parser.add_argument('--dry-run', action='store_true', help="Don't move any files")
    parser.add_argument('sources', action="store")
    args = parser.parse_args()

    sources = args.sources.split(',')
    main(sources, args.dry_run)
