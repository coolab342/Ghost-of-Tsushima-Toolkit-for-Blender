# -------------------------------------------------------------------
# Ghost of Tsushima Blender Tool
# Copyright (c) 2025 Dave349234
#
# This code is licensed under the MIT License with attribution requirements.
# See the LICENSE file in the root directory or the main __init__.py
# for full details.
#
# Profile: https://www.nexusmods.com/profile/Dave349234
# Support: https://ko-fi.com/dave349234
# -------------------------------------------------------------------

import struct
import math
import mathutils

GLOBAL_MATRIX = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
EXPORT_MATRIX = GLOBAL_MATRIX.inverted()

class GTVertexAttributeType:
    # known vertex buffer formats 
    # these ids correspond to specific data types (float, half, byte, etc.)
    Format_32_32_32_Float = 3254029       # position usually
    Format_16_16_16_Snorm = 3252492       # position (compressed)
    Format_16_16_Float = 2205445          # uvs
    Format_16_16_16_16_Unit = 11642124    # bone indices
    Format_8_8_8_8_Unorm = 11640842       # weights or colors
    Format_10_10_10_Snorm = 3252233       # normals / tangents (packed)
    Format_16_Float = 2107138             # extra data
    
    # unknown formats encountered in some meshes
    Format_Unk1 = 2105601 # uint16 
    Format_Unk2 = 107531  # float,float (8 byte)
    Format_Unk3 = 9220    # float (4 byte)
    Format_Unk4 = 9218    # int16 (2 byte)
    Format_Unk5 = 107525  # int32 (4 byte)

class BinaryReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.length = len(data)

    def seek(self, offset):
        self.pos = max(0, min(offset, self.length))

    def tell(self):
        return self.pos

    def read_bytes(self, length):
        val = self.data[self.pos : self.pos + length]
        self.pos += length
        return val

    # basic type readers using struct unpacking
    def read_int32(self): 
        return struct.unpack('<i', self.read_bytes(4))[0]
    
    def read_uint8(self): 
        return struct.unpack('<B', self.read_bytes(1))[0]
    
    def read_int16(self): 
        return struct.unpack('<h', self.read_bytes(2))[0]
    
    def read_uint16(self): 
        return struct.unpack('<H', self.read_bytes(2))[0]
    def read_uint32(self): 
        return struct.unpack('<I', self.read_bytes(4))[0]
    
    def read_uint64(self): 
        return struct.unpack('<Q', self.read_bytes(8))[0]
    
    def read_float(self): 
        return struct.unpack('<f', self.read_bytes(4))[0]
    
    def read_half(self): 
        return struct.unpack('<e', self.read_bytes(2))[0] # float16

    # vector readers
    def read_vec3(self): return struct.unpack('<3f', self.read_bytes(12))
    def read_vec4(self): return struct.unpack('<4f', self.read_bytes(16))

    # array readers
    def read_uint32_array(self, count):
        return struct.unpack(f'<{count}I', self.read_bytes(4*count))
    def read_uint64_array(self, count):
        return struct.unpack(f'<{count}Q', self.read_bytes(8*count))

    def read_string(self, length):
        val = self.read_bytes(length)
        try:
            return val.decode('ascii')
        except:
            return val.hex()

    def read_relative_offset_32(self):
        #common pattern, offset is relative to the current position
        return self.pos + self.read_int32()

class BinaryWriter:
    def __init__(self):
        self.data = bytearray()
        
    def write_bytes(self, b): 
        self.data.extend(b)

    def write_uint8(self, v): 
        self.data.extend(struct.pack('<B', v))

    def write_int16(self, v): 
        self.data.extend(struct.pack('<h', v))

    def write_uint16(self, v): 
        self.data.extend(struct.pack('<H', v))

    def write_int32(self, v): 
        self.data.extend(struct.pack('<i', v))

    def write_uint32(self, v): 
        self.data.extend(struct.pack('<I', v))

    def write_uint64(self, v): 
        self.data.extend(struct.pack('<Q', v))

    def write_float(self, v): 
        self.data.extend(struct.pack('<f', v))

    def write_half(self, v): 
        self.data.extend(struct.pack('<e', v))
    
    def get_bytes(self):
        return bytes(self.data)


def decode_pos(reader, attr, meta):
    # decodes a 16-bit snorm position using scale and offset from metadata
    raw_x = struct.unpack('<h', reader.read_bytes(2))[0]
    raw_y = struct.unpack('<h', reader.read_bytes(2))[0]
    raw_z = struct.unpack('<h', reader.read_bytes(2))[0]
    reader.read_bytes(2) # skip w or padding
    
    s = meta['scale']
    o = meta['offset']
    
    #formula: (raw / 32767.0) * scale + offset
    x = (raw_x / 32767.0) * s + o[0]
    y = (raw_y / 32767.0) * s + o[1]
    z = (raw_z / 32767.0) * s + o[2]
    
    return (x, y, z)

def encode_pos_16_snorm(vec, offset, scale):
    def pack(val, off, scl):
        norm = (val - off) / scl
        clamped = max(-1.0, min(1.0, norm))
        return int(clamped * 32767.0)

    x = pack(vec.x, offset[0], scale)
    y = pack(vec.y, offset[1], scale)
    z = pack(vec.z, offset[2], scale)
    return (x, y, z)

def unpack_10_10_10_2(value):
    # unpacks packed normals (10 bits x, 10 bits y, 10 bits z, 2 bits w)
    x = (value & 0x3FF) / 1023.0
    y = ((value >> 10) & 0x3FF) / 1023.0
    z = ((value >> 20) & 0x3FF) / 1023.0
    w = ((value >> 30) & 0x3) / 3.0
    return (x, y, z, w)

def pack_10_10_10_2(x, y, z, w=1.0):
    def to_10bit(v):
        # assume input is -1 to 1, map to 0 to 1
        norm = (v + 1.0) * 0.5
        clamped = max(0.0, min(1.0, norm))
        return int(clamped * 1023.0)
        
    def to_2bit(v):
        clamped = max(0.0, min(1.0, v))
        return int(clamped * 3.0)

    ix = to_10bit(x)
    iy = to_10bit(y)
    iz = to_10bit(z)
    iw = to_2bit(w)
    
    return ix | (iy << 10) | (iz << 20) | (iw << 30)