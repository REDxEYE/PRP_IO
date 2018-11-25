from pathlib import Path

from PIL import Image

from ByteIO import ByteIO


class PRP:

    def __init__(self, path: str):
        self.path = Path(path)
        self.reader = ByteIO(path=self.path)

        self.magic = b''
        self.model_name = ''
        self.textures = []
        self.meshes = []
        self.models = []
        self.materials = []

    def read(self):
        reader = self.reader
        self.magic = reader.read_fourcc()
        assert self.magic == 'RPK'
        reader.seek(16)
        self.model_name = reader.read_ascii_string(160)
        lst = reader.get_items()
        items = reader.filter_items(lst, 26)
        for item in items:
            reader.seek(item.offset)
            reader.skip(3)
            items2 = reader.get_items()
            for item2 in items2:
                reader.seek(item2.offset)
                # flag = reader.read_int32()
                flag = reader.read_fmt('BBBB')
                if flag in [(61, 0, 65, 0), (153, 0, 65, 0), (152, 0, 65, 0)]:
                    tex = Texture()
                    tex.read(reader)
                    self.textures.append(tex)

                elif flag == (53, 0, 65, 0):
                    mesh = Mesh()
                    mesh.read(reader)
                    self.meshes.append(mesh)
                elif flag in [(82, 6, 65, 0), (60, 6, 65, 0), (36, 6, 65, 0), (10, 6, 65, 0), (15, 6, 65, 0),
                              (8, 6, 65, 0),
                              (54, 6, 65, 0), (38, 6, 65, 0), (18, 6, 65, 0), (22, 6, 65, 0), (32, 6, 65, 0)]:
                    mat = Material()
                    mat.read(reader)
                    self.materials.append(mat)

                elif flag in [(75, 0, 65, 0)]:
                    mdl = Model()
                    mdl.read(reader)
                    self.models.append(mdl)


class Texture:

    def __init__(self):
        self.name = ''
        self.chunk_name = ''
        self.width = 0
        self.format = 0
        self.height = 0
        self.offset = 0

    def read(self, reader: ByteIO):
        header_chunks = reader.get_items()
        for tex_chunk in header_chunks:
            reader.seek(tex_chunk.offset)
            if tex_chunk.type == 20:
                self.chunk_name = reader.read_ascii_string(reader.read_int32())
            if tex_chunk.type == 21:
                self.name = Path(reader.read_ascii_string(reader.read_int32()))
            if tex_chunk.type == 1:
                texture_data_chunks = reader.get_items()
                for tex_data in texture_data_chunks:
                    reader.seek(tex_data.offset)
                    if tex_data.type == 20:
                        reader.skip(3)
                        items3 = reader.get_items()[:1]
                        for n, item3 in enumerate(items3):
                            reader.seek(item3.offset)
                            flag = reader.read_fmt('BBBB')
                            if flag == (36, 0, 65, 0):
                                items4 = reader.get_items()
                                for item4 in items4:
                                    reader.seek(item4.offset)
                                    if item4.type == 20:
                                        self.width = reader.read_int32()
                                    if item4.type == 21:
                                        self.height = reader.read_int32()
                                    if item4.type == 23:
                                        self.format = reader.read_int32()
                                    if item4.type == 22:
                                        self.offset = reader.tell()
                                reader.seek(self.offset)
                                if self.format == 7:
                                    pixel_mode = ('bcn', 1, 0)
                                elif self.format == 11:
                                    pixel_mode = ('bcn', 3, 0)
                                # elif self.format == 9:
                                #     pixel_mode = ('bcn', 1, 0)
                                # elif self.format == 5:
                                #     pixel_mode = ('bcn', 7, 0)
                                else:
                                    raise NotImplementedError('Format:{} is not supported yet'.format(self.format))
                                im_data = reader.read_bytes(self.width * self.height * 4)
                                image = Image.frombuffer('RGBA', (self.width, self.height), im_data, *pixel_mode)
                                del im_data
                                image.save(self.name.with_name(self.name.stem + str(n)).with_suffix('.tga'))


class Mesh:

    def __init__(self):
        self.chunk_name = ''
        self.name = ''
        self.indices_count = None
        self.indices_offset = 0
        self.indices = []
        self.mode = 0  # 0 - NONE,1 - triangles, 2 - triangle strip
        self.vert_stride = 0
        self.vert_count = 0
        self.vert_item_count = 0
        self.vert_offset = 0
        self.stream_offset = 0
        self.pos_offset = None
        self.uv_offset = None
        self.skin_ind_offset = None
        self.skin_weight_offset = None
        self.vertices = []
        self.uv = []
        self.weight_inds = []
        self.weight_weight = []
        ...

    def read(self, reader: ByteIO):
        header_chunks = reader.get_items()
        for item in header_chunks:
            reader.seek(item.offset)

            if item.type == 20:
                self.chunk_name = reader.read_ascii_string(reader.read_int32())
            if item.type == 21:
                self.name = reader.read_ascii_string(reader.read_int32())
            if item.type == 1:
                items = reader.get_items()
                for item in items:
                    reader.seek(item.offset)

                    if item.type == 10:
                        items2 = reader.get_items()
                        for item2 in items2:
                            reader.seek(item2.offset)
                            if item2.type == 21:
                                self.indices_count = reader.read_int32()
                            if item2.type == 22:
                                self.indices_offset = reader.tell()
                        if self.indices_count is not None:
                            self.mode = 1
                            reader.seek(self.indices_offset)
                            self.indices = [reader.read_uint16() for _ in range(self.indices_count)]

                    if item.type == 21:
                        items2 = reader.get_items()
                        for item2 in items2:
                            reader.seek(item2.offset)
                            if item2.type == 21:
                                self.indices_count = reader.read_int32()
                            if item2.type == 22:
                                self.indices_offset = reader.tell()
                        if self.indices_count is not None:
                            self.mode = 2
                            reader.seek(self.indices_offset)
                            self.indices = [reader.read_uint16() for _ in range(self.indices_count)]

                    if item.type == 11:
                        items2 = reader.get_items()
                        for item2 in items2:
                            reader.seek(item2.offset)
                            if item2.type == 20:
                                items3 = reader.get_items()
                                for item3 in items3:
                                    reader.seek(item3.offset)

                                    if item3.type == 21:
                                        self.vert_stride = reader.read_int32()
                                    if item3.type == 22:
                                        self.vert_item_count = reader.read_int32()
                                    if item3.type == 23:
                                        self.vert_offset = reader.tell()
                                    reader.seek(self.vert_offset)
                                off = 0
                                for k in range(self.vert_item_count):
                                    a, b, c, d = reader.read_fmt('BBBB')
                                    # print k,a,b,c,d,vertStrideSize
                                    if c == 1: self.pos_offset = off
                                    if c == 5 and a == 0:
                                        self.uv_offset = off
                                    # print k,a,b,c,d,vertStrideSize
                                    if c == 11: self.skin_ind_offset = off
                                    if c == 10: self.skin_weight_offset = off
                                    if d == 2: off += 12
                                    if d == 1: off += 8
                                    if d == 3: off += 16
                                    if d == 4: off += 1
                                    if d == 7: off += 1
                                    if d == 15: off += 4
                            if item2.type == 21:
                                self.vert_count = reader.read_int32()
                            if item2.type == 22:
                                self.stream_offset = reader.tell()
        reader.seek(self.stream_offset)
        for k in range(self.vert_count):
            tk = reader.tell()
            if self.pos_offset is not None:
                reader.seek(self.pos_offset + tk)
                self.vertices.append(reader.read_fmt('fff'))
            if self.uv_offset is not None:
                reader.seek(self.uv_offset + tk)
                self.uv.append(reader.read_fmt('ff'))
            if self.skin_ind_offset:
                reader.seek(self.skin_ind_offset + tk)
                self.weight_inds.append(reader.read_fmt('BBB'))
            if self.skin_weight_offset:
                reader.seek(self.skin_weight_offset + tk)
                self.weight_weight.append(reader.read_fmt('BBB'))
            reader.seek(tk + self.vert_stride)


class Material:

    def __init__(self):
        self.chunk_name = ''
        self.name = ''
        self.diffuse = ''
        ...

    def read(self, reader: ByteIO):
        items = reader.get_items()
        for item in items:
            reader.seek(item.offset)
            if item.type == 20:
                self.chunk_name = reader.read_ascii_string(reader.read_int32())
            if item.type == 21:
                self.name = reader.read_ascii_string(reader.read_int32())
            if item.type == 30:
                items2 = reader.get_items()
                for item2 in items2:
                    reader.seek(item2.offset)

                    if item2.type == 20:
                        self.diffuse = reader.read_ascii_string(reader.read_int32())

class Bone:

    def __init__(self):
        self.name = ''
        self.matrix = []
        self.parent = 0
        self.skin_id = 0

    def __repr__(self):
        return '<Bone "{}" parent:{}>'.format(self.name,self.parent)

class Model:

    def __init__(self):
        self.chunk_name = ''
        self.name = ''
        self.model_data = []
        self.stream_offset = 0
        self.bone_count = 0
        self.bones = []
        self.bone_map_list = []

    def read(self,reader:ByteIO):
        items = reader.get_items()
        for item in items:
            reader.seek(item.offset)
            if item.type == 20:
                self.chunk_name = reader.read_ascii_string(reader.read_int32())
            if item.type == 21:
                self.name = reader.read_ascii_string(reader.read_int32())
            if item.type == 30:
                items2 = reader.get_items()
                for item2 in items2:
                    reader.seek(item2.offset)
                    if item2.type == 1:
                        items3 = reader.get_items()
                        for item3 in items3:
                            reader.seek(item3.offset)
                            flag = reader.read_fmt('BBBB')
                            if flag == (103, 0, 65, 0):
                                mesh_chunk = None
                                mat_chunk = None
                                items4 = reader.get_items()
                                for item4 in items4:
                                    reader.seek(item4.offset)

                                    if item4.type == 31:
                                        items5 = reader.get_items()
                                        for item5 in items5:
                                            reader.seek(item5.offset)
                                            if item5.type == 20:
                                                mesh_chunk = reader.read_ascii_string(reader.read_int32())
                                    if item4.type == 33:
                                        items5 = reader.get_items()
                                        for item5 in items5:
                                            reader.seek(item5.offset)
                                            if item5.type == 20:
                                                mat_chunk = reader.read_ascii_string(reader.read_int32())
                                if mesh_chunk and mat_chunk:
                                    self.model_data.append([mesh_chunk,mat_chunk])
            if item.type == 33:
                items2 = reader.get_items()
                for item2 in items2:
                    reader.seek(item2.offset)
                    if item2.type == 20:
                        tmp = reader.read_int32()
                    if item2.type == 21:
                        self.bone_count = reader.read_int32()
                    if item2.type == 22:
                        self.stream_offset = reader.tell()
                reader.seek(self.stream_offset)
                if self.bone_count:
                    for m in range(self.bone_count):
                        tm = reader.tell()
                        bone = Bone()
                        bone.name = reader.read_ascii_string(32)
                        bone.matrix = reader.read_fmt('f'*16)
                        reader.skip(4*7)
                        bone.skin_id = reader.read_int32()
                        bone.parent = reader.read_int32()
                        reader.skip(4*3)
                        self.bones.append(bone)
                        reader.seek(tm+144)
            if item.type == 35:
                items2 = reader.get_items()
                for item2 in items2:
                    reader.seek(item2.offset)
                    if item2.type == 1:
                        items3 = reader.get_items()
                        for item3 in items3:
                            reader.seek(item3.offset)
                            flag = reader.read_fmt('BBBB')
                            if flag == (160, 0, 65, 0):
                                items4 = reader.get_items()
                                for item4 in items4:
                                    reader.seek(item4.offset)
                                    count = 0
                                    stream_offset = 0
                                    items5 = reader.get_items()
                                    for item5 in items5:
                                        reader.seek(item5.offset)
                                        if item5.type == 22:
                                            count = reader.read_int32()
                                        if item5.type == 23:
                                            stream_offset = reader.tell()
                                    if count:
                                        reader.seek(stream_offset)
                                        self.bone_map_list.extend([reader.read_int32() for _ in range(count)])






if __name__ == '__main__':
    a = PRP(r"E:\SteamLibrary\steamapps\common\Overlord II\Resources\Character Minion Bard.prp")
    a.read()
    ...
