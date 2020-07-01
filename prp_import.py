import json
import random
from pathlib import Path
from pprint import pprint
from typing import Dict, List

import bpy
import mathutils
from mathutils import *
from .prp_file import PRP, Bone, Model, Mesh, Material


def split(array, n=3):
    return [array[i:i + n] for i in range(0, len(array), n)]


def fix_matrix(matrix):
    t = matrix
    matrix = [[0.0, 0.0, 0.0, 0.0],
              [0.0, 0.0, 0.0, 0.0],
              [0.0, 0.0, 0.0, 0.0],
              [0.0, 0.0, 0.0, 0.0]]
    matrix[0][0] = t[0]
    matrix[1][0] = t[1]
    matrix[2][0] = t[2]
    matrix[3][0] = t[3]
    matrix[0][1] = t[4]
    matrix[1][1] = t[5]
    matrix[2][1] = t[6]
    matrix[3][1] = t[7]
    matrix[0][2] = t[8]
    matrix[1][2] = t[9]
    matrix[2][2] = t[10]
    matrix[3][2] = t[11]
    matrix[0][3] = t[12]
    matrix[1][3] = t[13]
    matrix[2][3] = t[14]
    matrix[3][3] = t[15]
    return matrix


class PRPIO:
    def __init__(self, path, import_textures=False, join_bones=False):
        # TODO: make import_textures to do stuff
        self.import_textures = import_textures
        self.path = Path(path)
        self.name = self.path.stem
        self.join_bones = join_bones
        self.prp_file = PRP(self.path)
        self.prp_file.read()

        # just a temp containers
        self.armature_obj = None
        self.armature = None
        self.mesh_obj = None
        self.mesh_data = None

        self.create_models()
        self.load_textures()

    # noinspection PyUnresolvedReferences
    @staticmethod
    def get_material(mat_name, model_ob):
        mat_name = mat_name if mat_name else 'Material'
        mat_ind = 0
        md = model_ob.data
        mat = None
        for candidate in bpy.data.materials:  # Do we have this material already?
            if candidate.name == mat_name:
                mat = candidate
        if mat:
            if md.materials.get(mat.name):  # Look for it on this mesh_data
                for i in range(len(md.materials)):
                    if md.materials[i].name == mat.name:
                        mat_ind = i
                        break
            else:  # material exists, but not on this mesh_data
                md.materials.append(mat)
                mat_ind = len(md.materials) - 1
        else:  # material does not exist
            mat = bpy.data.materials.new(mat_name)
            md.materials.append(mat)
            # Give it a random colour
            rand_col = [random.uniform(.4, 1) for _ in range(3)]
            rand_col.append(1.0)
            mat.diffuse_color = rand_col

            mat_ind = len(md.materials) - 1

        return mat_ind

    def create_skeleton(self, bone_data: List[Bone], normal_bones=False):

        bpy.ops.object.armature_add(enter_editmode=True)

        self.armature_obj = bpy.data.objects.new(self.name + "_ARM", bpy.data.armatures.new(self.name + "_ARM_DATA"))
        self.armature_obj.show_in_front = True
        self.armature = self.armature_obj.data
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.collection.objects.link(self.armature_obj)
        bpy.ops.object.select_all(action="DESELECT")
        self.armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = self.armature_obj

        bpy.ops.object.mode_set(mode='EDIT')
        bones = []
        for se_bone in bone_data:  # type: Bone
            bones.append((self.armature.edit_bones.new(se_bone.name), se_bone))

        for bl_bone, se_bone in bones:  # type: bpy.types.EditBone, Bone
            if se_bone.parent != -1:
                bl_parent, parent = bones[se_bone.parent]
                bl_bone.parent = bl_parent
            bl_bone.tail = Vector([0, 0, 1]) + bl_bone.head

        bpy.ops.object.mode_set(mode='POSE')
        for se_bone in bone_data:  # type:Bone
            bl_bone = self.armature_obj.pose.bones.get(se_bone.name)
            mat = Matrix(fix_matrix(se_bone.matrix))
            bl_bone.matrix_basis.identity()
            bl_bone.matrix = (bl_bone.parent.matrix @ mat) if bl_bone.parent else mat
        bpy.ops.pose.armature_apply()
        bpy.ops.object.mode_set(mode='EDIT')
        if normal_bones:
            for name, bl_bone in self.armature.edit_bones.items():
                if not bl_bone.parent:
                    continue
                parent = bl_bone.parent
                if len(parent.children) > 1:
                    bl_bone.use_connect = False
                    parent.tail = sum(
                        (ch.head for ch in parent.children), mathutils.Vector()
                    ) / len(parent.children)

                else:
                    parent.tail = bl_bone.head
                    bl_bone.use_connect = True
                    if bl_bone.children == 0:
                        par = bl_bone.parent
                        if par.children > 1:
                            bl_bone.tail = bl_bone.head + (par.tail - par.head)
                    if bl_bone.parent == 0 and bl_bone.children > 1:
                        bl_bone.tail = (bl_bone.head + bl_bone.tail) * 2
                if not bl_bone.children:
                    vec = bl_bone.parent.head - bl_bone.head
                    bl_bone.tail = bl_bone.head - vec / 2
            bpy.ops.armature.calculate_roll(type='GLOBAL_POS_Z')
        bpy.ops.object.mode_set(mode='OBJECT')

    @staticmethod
    def strip_to_list(indices):
        new_indices = []
        for v in range(len(indices) - 2):
            new_indices.append(indices[v])
            if v & 1:
                new_indices.append(indices[v + 1])
                new_indices.append(indices[v + 2])
            else:
                new_indices.append(indices[v + 2])
                new_indices.append(indices[v + 1])
        new_indices = list(filter(lambda a: len(set(a)) == 3, split(new_indices)))
        return new_indices

    def build_meshes(self, model_data: Model):

        # base_name = mesh_data['name']
        for m, (mesh_id, mat_id) in enumerate(model_data.meshes):
            mesh: Mesh = self.prp_file.meshes[mesh_id]
            # pprint(mesh_json)
            if mat_id in self.prp_file.materials:
                material_name = self.prp_file.materials[mat_id].name
            else:
                material_name = mat_id
            name = model_data.name
            mesh_obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
            bpy.context.scene.collection.objects.link(mesh_obj)
            mesh_data = mesh_obj.data
            if self.armature_obj:
                mesh_obj.parent = self.armature_obj

                modifier = mesh_obj.modifiers.new(type="ARMATURE", name="Armature")
                modifier.object = self.armature_obj

            # bones = [bone_list[i] for i in remap_list]

            if model_data.bones:
                print('Bone list available, creating vertex groups')
                weight_groups = {bone.name: mesh_obj.vertex_groups.new(name=bone.name) for bone in
                                 model_data.bones}
            uvs = mesh.uv
            print('Building mesh:', name)
            print('Mesh mode:', mesh.mode)
            assert mesh.mode == 2
            new_indices = self.strip_to_list(mesh.indices)
            mesh_data.from_pydata(mesh.vertices, [], new_indices)
            mesh_data.update()
            mesh_data.uv_layers.new()
            uv_data = mesh_data.uv_layers[0].data
            for i in range(len(uv_data)):
                u = uvs[mesh_data.loops[i].vertex_index]
                uv_data[i].uv = u
            if model_data.bones:
                for n, (bones, weights) in enumerate(
                        zip(mesh.weight_inds, mesh.weight_weight)):
                    for bone, weight in zip(bones, weights):
                        if weight != 0:
                            # if bone in mesh_data['bone_map']:
                            bone_id = model_data.bone_map_list[m][bone]
                            bone_name = model_data.name_list[bone_id]  # ['name']
                            weight_groups[bone_name].add([n], weight / 255, 'REPLACE')
            self.get_material(material_name, mesh_obj)
            bpy.ops.object.select_all(action="DESELECT")
            mesh_obj.select_set(True)
            bpy.context.view_layer.objects.active = mesh_obj
            bpy.ops.object.shade_smooth()
            # mesh.normals_split_custom_set(normals)
            mesh.use_auto_smooth = True

    def create_models(self):
        for model in self.prp_file.models:
            # pprint(model)
            if model.bone_count > 0:
                self.create_skeleton(model.bones, self.join_bones)
            else:
                self.armature = None
                self.armature_obj = None
            self.build_meshes(model)

    def load_textures(self):
        for texture in self.prp_file.textures.values():
            image = bpy.data.images.new(
                texture.name,
                width=texture.width,
                height=texture.height)
            image.pixels = texture.image_data
            image.name = texture.chunk_name
            image.pack()


if __name__ == '__main__':
    a = PRPIO(r"D:\SteamLibrary\steamapps\common\Overlord II\Resources\dump\Character Minion Bard\model.json")
