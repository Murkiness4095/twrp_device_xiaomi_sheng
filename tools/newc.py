# SPDX-License-Identifier: Apache-2.0
import stat
from pathlib import Path

def unpack_cpio(data, destination):
    # Do not create device nodes or follow ramdisk symlinks while extracting.
    destination.mkdir(parents=True, exist_ok=False)
    links, offset, entries = [], 0, 0
    while offset + 110 <= len(data):
        header = data[offset:offset + 110]
        if header[:6] not in (b'070701', b'070702'):
            raise ValueError(f'Invalid newc header at {offset}')
        values = [int(header[6 + i * 8:14 + i * 8], 16) for i in range(13)]
        mode, size, namesize = values[1], values[6], values[11]
        offset += 110
        name = data[offset:offset + namesize - 1].decode()
        offset = (offset + namesize + 3) & ~3
        content = data[offset:offset + size]
        offset = (offset + size + 3) & ~3
        if name == 'TRAILER!!!':
            break
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError(f'Unsafe cpio path: {name}')
        target = destination / path
        entries += 1
        if stat.S_ISDIR(mode):
            target.mkdir(parents=True, exist_ok=True)
        elif stat.S_ISREG(mode):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(mode & 0o777)
        elif stat.S_ISLNK(mode):
            links.append((target, content.decode()))
    for target, link in links:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(link)
    return entries
