#!/usr/bin/env python3

import os
import sys
import errno
import fusefs as fs
import argparse

from utilities import first
from fuse import FUSE, FuseOSError


class DuplicatePathException(Exception):
    pass


class Filesystem():

    def __call__(self, op, *args):
        if not hasattr(self, op):
            raise FuseOSError(errno.EFAULT)
        return getattr(self, op)(*args)

    def __init__(self, sources, mountpoint):
        self.sources = sources
        self.mountpoint = mountpoint
        self._check_for_duplicates()

    def access(self, path, mode):
        return fs.access(self._full_path(path), mode)

    def chmod(self, path, mode):
        return fs.chmod(self._full_path(path), mode)

    def chown(self, path, uid, gid):
        return fs.chown(self._full_path(path), uid, gid)

    def getattr(self, path, fh=None):
        return fs.getfileattr(self._full_path(path), fh)

    def mknod(self, path, mode, dev):
        return fs.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        return fs.rmdir(self._full_path(path))

    def mkdir(self, path, mode):
        return fs.mkdir(self._full_path(path), mode)

    def unlink(self, path):
        return fs.unlink(self._full_path(path))

    def symlink(self, source, target):
        return fs.symlink(self._full_path(source), self._full_path(target))

    def rename(self, old, new):
        return fs.rename(self._full_path(old), self._full_path(new))

    def link(self, source, target):
        return fs.link(self._full_path(source), self._full_path(target))

    def utimens(self, path, times=None):
        return fs.utimens(self._full_path(path), times)

    def open(self, path, flags):
        return fs.openFile(self._full_path(path), flags)

    def create(self, path, mode, fi=None):
        return fs.create(self._full_path(path), mode, fi)

    def read(self, path, length, offset, fh):
        return fs.read(self._full_path(path), length, offset, fh)

    def write(self, path, buf, offset, fh):
        return fs.write(self._full_path(path), buf, offset, fh)

    def truncate(self, path, length, fh=None):
        return fs.truncate(self._full_path(path), length, fh)

    def flush(self, path, fh):
        return fs.flush(self._full_path(path), fh)

    def release(self, path, fh):
        return fs.release(self._full_path(path), fh)

    def fsync(self, path, fdatasync, fh):
        return fs.fsync(self._full_path(path), fdatasync, fh)

    def statfs(self, path):
        if path == '/':
            return self._root_statfs()
        else:
            return fs.statfs(self._full_path(path))

    def readdir(self, path, fh):
        if path == '/':
            return self._root_readdir(fh)
        else:
            return fs.readdir(self._full_path(path), fh)

    def readlink(self, path):
        pathname = fs.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.mountpoint)
        else:
            return pathname

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
        return fs.statfs(source)['f_bfree']

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

    def _root_readdir(self, fh):
        # When reading the root we need to merge all of the sources
        dirents = ['.', '..']
        for source in self.sources:
            dirents.extend(os.listdir(source))
        
        for r in dirents:
            yield r

    def _root_statfs(self):
        # The file attributes for the root dir are tricky -- they can't be merged perfectly
        # Present an optimistic number for the available blocks -- even though one directory must fit within one source
        # TODO this assumes all sources have the same blocksize (f_frsize).
        stvs = [fs.statfs(source) for source in self.sources]

        root_stv = {} 
        root_stv["f_bavail"] = sum((stv['f_bavail'] for stv in stvs))
        root_stv["f_bfree"] = sum((stv['f_bfree'] for stv in stvs))
        root_stv["f_blocks"] = sum((stv['f_blocks'] for stv in stvs))
        root_stv["f_bsize"] = first((stv['f_bsize'] for stv in stvs))
        root_stv["f_favail"] = sum((stv['f_favail'] for stv in stvs))
        root_stv["f_ffree"] = sum((stv['f_ffree'] for stv in stvs))
        root_stv["f_files"] = sum((stv['f_files'] for stv in stvs))
        root_stv["f_flag"] = first((stv['f_flag'] for stv in stvs))
        root_stv["f_frsize"] = first((stv['f_frsize'] for stv in stvs))
        root_stv["f_namemax"] = min((stv['f_namemax'] for stv in stvs))
        return root_stv

def parse_mount_options(options):
    dict_options = {}
    for option in options.split(","):
        if '=' in option:
            key, value = option.split('=')
            dict_options[key] = value
        else:
            dict_options[option] = True
    return dict_options

def main(sources, mountpoint, options=''):
    cfs = Filesystem(sources, mountpoint)
    mount_options = parse_mount_options(options)
    # FUSE(cfs, mountpoint, nothreads=True, foreground=True, **{'allow_other': True})
    FUSE(cfs, mountpoint, nothreads=True, **mount_options)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The Cinch Filesystem')
    parser.add_argument('sources', action="store")
    parser.add_argument('mountpoint', action="store")
    parser.add_argument('-o', action="store", dest="options")
    #TODO or create a configuration file that you pass the path of
    args = parser.parse_args()

    sources = args.sources.split(',')
    main(sources, args.mountpoint, args.options)

