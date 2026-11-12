"""Bounded CSO1 reference codec. This format is independent of kernel swap codecs."""
import struct
import zlib

PAGE_SIZE = 4096
MAX_INPUT = 1024 * 1024
HEADER = struct.Struct('<4sII')
BLOCK = struct.Struct('<BH')
MAX_CONTAINER = HEADER.size + MAX_INPUT + (MAX_INPUT // PAGE_SIZE) * BLOCK.size


class CodecError(ValueError):
    pass


def encode_page(page):
    """RLE pairs: one byte (run length minus one), one byte value."""
    encoded = bytearray()
    index = 0
    while index < len(page):
        end = index + 1
        while end < len(page) and end - index < 256 and page[end] == page[index]:
            end += 1
        encoded.extend((end - index - 1, page[index]))
        index = end
    return bytes(encoded)


def pack(data, encoded_pages):
    if len(data) > MAX_INPUT:
        raise CodecError('input exceeds 1 MiB')
    output = bytearray(HEADER.pack(b'CSO1', len(data), zlib.crc32(data)))
    pages = [data[i:i + PAGE_SIZE] for i in range(0, len(data), PAGE_SIZE)]
    if len(encoded_pages) != len(pages):
        raise CodecError('incorrect page count')
    for page, encoded in zip(pages, encoded_pages):
        compressed = len(encoded) < len(page)
        payload = encoded if compressed else page
        output.extend(BLOCK.pack(int(compressed), len(payload)))
        output.extend(payload)
    return bytes(output)


def compress(data):
    if len(data) > MAX_INPUT:
        raise CodecError('input exceeds 1 MiB')
    return pack(data, [encode_page(data[i:i + PAGE_SIZE])
                       for i in range(0, len(data), PAGE_SIZE)])


def decompress(container):
    if not HEADER.size <= len(container) <= MAX_CONTAINER:
        raise CodecError('invalid container size')
    magic, size, checksum = HEADER.unpack_from(container)
    if magic != b'CSO1' or size > MAX_INPUT:
        raise CodecError('invalid header')
    output = bytearray()
    offset = HEADER.size
    while len(output) < size:
        expected = min(PAGE_SIZE, size - len(output))
        if offset + BLOCK.size > len(container):
            raise CodecError('truncated block header')
        mode, length = BLOCK.unpack_from(container, offset)
        offset += BLOCK.size
        if mode not in (0, 1) or length == 0 or length > expected:
            raise CodecError('invalid block')
        payload = container[offset:offset + length]
        if len(payload) != length:
            raise CodecError('truncated block')
        offset += length
        if mode == 0:
            if length != expected:
                raise CodecError('incorrect raw block length')
            output.extend(payload)
        else:
            if length % 2:
                raise CodecError('invalid RLE pairs')
            page = bytearray()
            for index in range(0, length, 2):
                count = payload[index] + 1
                if len(page) + count > expected:
                    raise CodecError('RLE expansion exceeds page')
                page.extend(bytes((payload[index + 1],)) * count)
            if len(page) != expected:
                raise CodecError('incorrect expanded length')
            output.extend(page)
    if offset != len(container) or zlib.crc32(output) != checksum:
        raise CodecError('trailing bytes or checksum mismatch')
    return bytes(output)
