import bpy
import bpy_types
from mathutils import *
from progress_report import ProgressReport, ProgressReportSubstep
import os
from . import seanim as SEAnim

def export_action(self, context, action, filepath):
	print("%s -> %s" % (action.name, filepath)) # DEBUG
	ob = bpy.context.object

	anim = SEAnim.Anim()

	anim.header.frameCount = int(action.frame_range[1])
	anim.header.framerate = context.scene.render.fps

	bones = {}
	for pose_bone in ob.pose.bones:
		bone = SEAnim.Bone()
		bone.name = pose_bone.name

		anim.bones.append(bone)

	for pose_marker in action.pose_markers:
		note = SEAnim.Note()
		note.frame = pose_marker.frame
		note.name = pose_marker.name
		anim.notes.append(note)

	print("Saving %s" % filepath)
	anim.save(filepath)

def save(self, context):
	ob = bpy.context.object
	if ob.type != 'ARMATURE':
		return {'CANCELLED'}

	prefix = os.path.basename(self.filepath)
	path = os.path.dirname(self.filepath) + "\\"

	with ProgressReport(context.window_manager) as progress:
		if self.use_actions:
			for action in bpy.data.actions:
				export_action(self, context, action, path + prefix + action.name + ".seanim")
		else:
			export_action(self, context, bpy.context.object.animation_data.action, self.filepath)

	return {'FINISHED'}
