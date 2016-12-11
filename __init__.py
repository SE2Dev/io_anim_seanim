bl_info = {
	"name": "SEAnim Support",
	"author": "SE2Dev", 
	"version": (0, 2, 0),
	"blender": (2, 62, 3),
	"location": "File > Import",
	"description": "Import SEAnim",
	"warning": "ADDITIVE animations are not currently supported",
	"wiki_url": "https://github.com/SE2Dev/io_anim_seanim",
	"tracker_url": "https://github.com/SE2Dev/io_anim_seanim/issues",
	"support": "COMMUNITY",
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

	@classmethod
	def poll(self, context):
		if context.active_object is not None:
			if context.active_object.type == 'ARMATURE':
				return True
			
			# Currently Disabled
			#elif context.active_object.parent is not None:
			#	return context.active_object.parent.type == 'ARMATURE'

		return False

class ExportSEAnim(bpy.types.Operator, ExportHelper):
	bl_idname = "export_scene.seanim"
	bl_label = "Export SEAnim"
	bl_description = "Export an SEAnim"
	bl_options = {'PRESET'}

	filename_ext = ".seanim"
	filter_glob = StringProperty(default="*.seanim", options={'HIDDEN'})

	files = CollectionProperty(type=bpy.types.PropertyGroup)

	anim_type = EnumProperty(
			name="Anim Type",
			description="Choose between two items",
			items=(	('OPT_ABSOLUTE', "Absolute", "Used for viewmodel animations"),
					#('OPT_ADDITIVE', "Additive", "Used for some idle animations"), # Currently Disabled
					('OPT_RELATIVE', "Relative", "Used for most animations"),
					('OPT_DELTA',    "Delta",    "Used for walk cycles")),
			default='OPT_RELATIVE',
			)

	key_types = EnumProperty(
			name="Keyframe Types",
			description="Export specific keyframe types",
			options={'ENUM_FLAG'},
			items=(('LOC', "Location", ""),
				   ('ROT', "Rotation", ""),
				   #('SCALE', "Scale", ""), # Not Currently Supported
				   ),
			default={'LOC', 'ROT'}, #, 'SCALE'},
			)

	every_frame = BoolProperty(
		name="Every Frame",
		description="Automatically generate keyframes for every single frame",
		default=False)

	high_precision = BoolProperty(
		name="High Precision",
		description="Use double precision floating point values for quaternions and vectors (Note: Increases file size)",
		default=False)

	is_looped = BoolProperty(
		name="Looped",
		description="Mark the animation as a looping animation",
		default=False)

	use_actions = BoolProperty(
			name="Export All Actions",
			description="Export all actions to the target path",
			default=False)

	# PREFIX & SUFFIX Require "use_actions" to be true and are enabled / disabled from __update_use_actions
	prefix = StringProperty(
		name="File Prefix",
		description="The prefix string that is applied to the beginning of the filename for each exported action",
		default="")

	suffix = StringProperty(
		name="File Suffix",
		description="The suffix string that is applied to the end of the filename for each exported action",
		default="")

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "anim_type")

		row = layout.row()
		row.label("Include:")
		row.prop(self, "key_types")

		layout.prop(self, "high_precision")
		layout.prop(self, "is_looped")
		layout.prop(self, "every_frame")

		box = layout.box()
		box.prop(self, "use_actions")
		if(self.use_actions):
			box.prop(self, "prefix")
			box.prop(self, "suffix")

	def execute(self, context):
		# print("Selected: " + context.active_object.name)
		from . import export_seanim
		return export_seanim.save(self, context)

	@classmethod
	def poll(self, context):
		ob = context.active_object
		if ob is not None:
			if ob.type == 'ARMATURE' and ob.animation_data is not None:
				return True
			
			# Currently Disabled
			#elif context.active_object.parent is not None:
			#	return context.active_object.parent.type == 'ARMATURE'
			
		return False

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
