#!/usr/bin/env python

import os
import sys
import errno

from fuse import FUSE, FuseOSError, Operations
from passthrough import Passthrough


class DuplicatePathException(Exception):
    pass


def first(iterable, default=None, key=None):
    if key is None:
        for el in iterable:
            if el:
                return el
    else:
        for el in iterable:
            if key(el):
                return el
    return default


class cinchfs(Passthrough):
    def __init__(self, sources):
        self.sources = sources
        self._check_for_duplicates()

    def _check_for_duplicates(self):
        # it is enough to check that there are no duplicates in the root directory of all sources
        seen = set()
        for source in self.sources:
            entities = set(os.listdir(source))
            duplicates = entities.intersection(seen)
            if len(duplicates) > 0:
                raise DuplicatePathException() 
            seen.update(entities)

    def _find_source_with_most_free_blocks(self):
        return max(self.sources, key=self._get_free_blocks)

    def _get_free_blocks(self, source):
        fd = os.open(source, os.O_RDONLY)
        stv = os.fstatvfs(fd)
        os.close(fd)
        return stv.f_bfree

    def _full_path(self, partial):
        # all provided paths are full with the mountpoint as the root
        if partial.startswith('/'):
            partial = partial[1:]

        # re-use an existing file or dir
        for source in self.sources:
            path = os.path.join(source, partial)
            if os.path.exists(path):
                return path

        # if a base dir exists, then use that source
        path_parts = partial.split(os.path.sep)
        if len(path_parts) > 1:
            # path is more than just a filename
            base_dir = path_parts[0]
            for source in self.sources:
                base_path = os.path.join(source, base_dir)
                if os.path.exists(base_path):
                    return os.path.join(source, partial)

        # use disk with most free space
        source = self._find_source_with_most_free_blocks()
        return os.path.join(source, partial)

    def readdir(self, partial, fh):
        print('readdir', partial, fh)
        dirents = ['.', '..']

        if partial == '/':
            for source in self.sources:
                dirents.extend(os.listdir(source))
        else:
            full_path = self._full_path(partial)
            if os.path.isdir(full_path):
                dirents.extend(os.listdir(full_path))
        
        for r in dirents:
            yield r


    def _root_statfs(self):
        stvs = []
        for source in sources:
            fd = os.open(source, os.O_RDONLY)
            stv = os.fstatvfs(fd)
            print(source, stv)
            stvs.append(stv)
            os.close(fd)
       
        # f_frsize=4096, f_blocks=1937841596
        # caveat: assuming all disks have the same block size
        root_stv = {} 
        root_stv["f_bavail"] = sum((stv.f_bavail for stv in stvs))
        root_stv["f_bfree"] = sum((stv.f_bfree for stv in stvs))
        root_stv["f_blocks"] = sum((stv.f_blocks for stv in stvs))
        root_stv["f_bsize"] = first((stv.f_bsize for stv in stvs))
        root_stv["f_favail"] = sum((stv.f_favail for stv in stvs))
        root_stv["f_ffree"] = sum((stv.f_ffree for stv in stvs))
        root_stv["f_files"] = sum((stv.f_files for stv in stvs))
        root_stv["f_flag"] = first((stv.f_flag for stv in stvs))
        root_stv["f_frsize"] = first((stv.f_frsize for stv in stvs))
        root_stv["f_namemax"] = min((stv.f_namemax for stv in stvs))
        return root_stv

    # override to fudge df to include all disks instead of just the first one
    def statfs(self, partial):
        print('statfs', partial)

        if partial == '/':
            return self._root_statfs()

        full_path = self._full_path(partial)
        fd = os.open(full_path, os.O_RDONLY)
        stv = os.fstatvfs(fd)
        os.close(fd)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

def main(sources, mountpoint):
    cfs = cinchfs(sources)
    # FUSE(cfs, mountpoint, nothreads=True, foreground=True, **{'allow_other': True})
    FUSE(cfs, mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    sources = sys.argv[1:-1]
    mountpoint = sys.argv[-1]
    main(sources, mountpoint)

