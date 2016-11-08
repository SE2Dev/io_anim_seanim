bl_info = {
	"name": "SEAnim Support",
	"author": "SE2Dev", 
	"version": (0, 1, 0),
	"blender": (2, 62, 3),
	"location": "File > Import",
	"description": "Import SEAnim",
	"warning": "Alpha version, please report any bugs!",
	"wiki_url": "",
	"tracker_url": "",
	"support": "TESTING",
	"category": "Import-Export"
}

import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import BoolProperty, IntProperty, FloatProperty, StringProperty, EnumProperty, CollectionProperty

# To support reload properly, try to access a package var, if it's there, reload everything
if "bpy" in locals():
	import imp
	if "import_seanim" in locals():
		imp.reload(import_seanim)
else:
	from . import import_seanim

import bpy_extras.io_utils
from bpy_extras.io_utils import ExportHelper, ImportHelper
import time

class ImportSEAnim(bpy.types.Operator, ImportHelper):
	bl_idname = "import_scene.seanim"
	bl_label = "Import SEAnim"
	bl_description = "Import one or more SEAnim files"
	bl_options = {'PRESET'}

	filename_ext = ".seanim"
	filter_glob = StringProperty(default="*.seanim", options={'HIDDEN'})

	files = CollectionProperty(type=bpy.types.PropertyGroup)

	def execute(self, context):
		# print("Selected: " + context.active_object.name)
		from . import import_seanim
		return import_seanim.load(self, context, **self.as_keywords(ignore=("filter_glob", "files")))

class ExportSEAnim(bpy.types.Operator, ImportHelper):
	bl_idname = "export_scene.seanim"
	bl_label = "Export SEAnim"
	bl_description = "Export an SEAnim"
	bl_options = {'PRESET'}

	filename_ext = ".seanim"
	filter_glob = StringProperty(default="*.seanim", options={'HIDDEN'})

	files = CollectionProperty(type=bpy.types.PropertyGroup)

	def execute(self, context):
		# print("Selected: " + context.active_object.name)
		from . import export_seanim
		return export_seanim.save(self, context)

def get_operator(idname):
	op = bpy.ops
	for attr in idname.split("."):
		op = getattr(op, attr)
	return op

def menu_func_seanim_import(self, context):
	self.layout.operator(ImportSEAnim.bl_idname, text="SEAnim (.seanim)")

def menu_func_seanim_export(self, context):
	self.layout.operator(ExportSEAnim.bl_idname, text="SEAnim (.seanim)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_import.append(menu_func_seanim_import)
	bpy.types.INFO_MT_file_export.append(menu_func_seanim_export)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_import.remove(menu_func_seanim_import)
	bpy.types.INFO_MT_file_export.remove(menu_func_seanim_export)
 
if __name__ == "__main__":
	register()
