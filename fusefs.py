#!/usr/bin/env python3

import os
import errno

from fuse import FuseOSError

def access(path, mode):
    '''Check file access permissions. This will be called for the access() system call. 
    If the 'default_permissions' mount option is given, this method is not called.'''
    if not os.access(path, mode):
        raise FuseOSError(errno.EACCES)

def chmod(path, mode):
    '''Change the permission bits of a file'''
    return os.chmod(path, mode)

def chown(path, uid, gid):
    '''Change the owner and group of a file'''
    return os.chown(path, uid, gid)

def getfileattr(path, fh=None):
    '''Get file attributes'''
    st = os.lstat(path)
    return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime', 'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid', 'st_blocks'))

def readdir(path, fh):
    '''Read directory'''
    dirents = ['.', '..']
    if os.path.isdir(path):
        dirents.extend(os.listdir(path))

    for r in dirents:
        yield r

def readlink(path):
    '''Read the target of a symbolic link'''
    return os.readlink(path)

def mknod(path, mode, dev):
    return os.mknod(path, mode, dev)

def rmdir(path):
    return os.rmdir(path)

def mkdir(path, mode):
    return os.mkdir(path, mode)

def statfs(path):
    fd = os.open(path, os.O_RDONLY)
    stv = os.fstatvfs(fd)
    os.close(fd)
    return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree', 'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag', 'f_frsize', 'f_namemax'))

def unlink(path):
    return os.unlink(path)

def symlink(source, target):
    return os.symlink(target, source)

def rename(old, new):
    return os.rename(old, new)

def link(source, target):
    return os.link(source, target)

def utimens(path, times=None):
    return os.utime(path, times)

def openFile(path, flags):
    return os.open(path, flags)

def create(path, mode, fi=None):
    return os.open(path, os.O_WRONLY | os.O_CREAT, mode)

def read(path, length, offset, fh):
    os.lseek(fh, offset, os.SEEK_SET)
    return os.read(fh, length)

def write(path, buf, offset, fh):
    os.lseek(fh, offset, os.SEEK_SET)
    return os.write(fh, buf)

def truncate(path, length, fh=None):
    '''Change the size of a file'''
    with open(path, 'r+') as f:
        f.truncate(length)

def flush(path, fh):
    '''Possibly flush cached data'''
    return os.fsync(fh)

def release(path, fh):
    '''Release an open file'''
    return os.close(fh)

def fsync(path, fdatasync, fh):
    '''Synchronize file contents'''
    return flush(path, fh)
