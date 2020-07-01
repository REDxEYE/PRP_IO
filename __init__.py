import bpy
from pathlib import Path

bl_info = {
    "name": "Overlord2 model import + textures",
    "author": "RED_EYE",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "File > Import-Export > Overlord2 model (.prp) ",
    "description": "Addon allows to import Overlord2 models",
    "category": "Import-Export"
}

from bpy.props import StringProperty, BoolProperty, CollectionProperty


class Overlord2_OT_operator(bpy.types.Operator):
    """Load Overlord2 prp(converted to json) models"""
    bl_idname = "import_mesh.prp"
    bl_label = "Import Overlord2 model"
    bl_options = {'UNDO'}

    filepath = StringProperty(
        subtype='FILE_PATH',
    )
    files = CollectionProperty(name='File paths', type=bpy.types.OperatorFileListElement)
    normal_bones = BoolProperty(name="Make normal skeleton?", default=False, subtype='UNSIGNED')
    filter_glob = StringProperty(default="*.prp", options={'HIDDEN'})

    def execute(self, context):
        from . import prp_import
        directory = Path(self.filepath).parent.absolute()
        for file in self.files:
            importer = prp_import.PRPIO(str(directory / file.name), join_bones=self.normal_bones)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_import(self, context):
    self.layout.operator(Overlord2_OT_operator.bl_idname, text="Overlord2 model (.prp)")

classes = (Overlord2_OT_operator,)
register_, unregister_ = bpy.utils.register_classes_factory(classes)


def register():
    register_()
    bpy.types.TOPBAR_MT_file_import.append(menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    unregister_()


if __name__ == "__main__":
    register()
