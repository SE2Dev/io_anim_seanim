import bpy
import bpy_types
from mathutils import *
from progress_report import ProgressReport, ProgressReportSubstep
import os
from . import seanim as SEAnim

# TODO: Add support for defining modifier bones for Absolute anims

def get_loc_vec(bone, anim_type):
	if anim_type == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE and bone.parent is not None:
		return bone.parent.matrix.inverted() * bone.matrix.translation
	return bone.matrix_basis.translation

# TODO: Support for SEANIM_TYPE_ADDITIVE
def get_rot_quat(bone, anim_type):
	# Absolute, Relative, and Delta all use the same rotation formula
	try:
		bone.parent.matrix
	except:
		# Lets just return the matrix as a quaternion for now - it mirrors what the importer does
		return bone.matrix.to_quaternion()
	else:
		mtx = bone.parent.matrix.to_3x3()
		return (mtx.inverted() * bone.matrix.to_3x3()).to_quaternion()

def export_action(self, context, progress, action, filepath):
	#print("%s -> %s" % (action.name, filepath)) # DEBUG
	
	ob = bpy.context.object
	frame_original = context.scene.frame_current

	anim = SEAnim.Anim()

	"""
		For whatever reason - an action with a single keyframe (ex: on frame 1) will have a range of (ex: Vector((1.0, 2.0)))
			However, an action with a keyframe on both frame 1 and frame 2 will have the same frame range.

		To make up for this - we assume frame_range[1] - frame_range[0] + 1 is the number of frames in the action
		For actions that only have keyframes on a single frame, this must be corrected later...
	"""
	frame_start = int(action.frame_range[0])
	anim.header.frameCount = int(action.frame_range[1]) - int(action.frame_range[0])
	anim.header.framerate = context.scene.render.fps

	anim_bones = {}

	for pose_bone in ob.pose.bones:
		anim_bone = SEAnim.Bone()
		anim_bone.name = pose_bone.name
		anim_bones[pose_bone.name] = anim_bone

	frames = {}

	# Step 1: Analyzing Keyframes
	# Resolve the relevent keyframe indices for loc, rot, and / or scale for each bone
	for fc in action.fcurves:
		try:
			prop = ob.path_resolve(fc.data_path, False) # coerce=False
			if type(prop.data) != bpy_types.PoseBone:
				raise
			pose_bone = prop.data

			if prop == pose_bone.location.owner:
				#print("LOC")
				index = 0
			elif prop == pose_bone.rotation_quaternion.owner or prop == pose_bone.rotation_euler.owner or prop == pose_bone.rotation_axis_angle.owner:
				#print("ROT")
				index = 1
			elif owner is pose_bone.scale.owner:
				#print("SCALE")
				index = 2
			else:
				print("ERR: %s" % prop)
				raise
		except Exception as e: # If the fcurve isn't for a valid property, just skip it
			#print("skipping : %s" % e) # DEBUG
			pass
		else:
			for key in fc.keyframe_points:
				f = int(key.co[0])
				if frames.get(f) is None:
					frames[f] = {}
				frame_bones = frames[f]
				if frame_bones.get(pose_bone.name) is None:
					frame_bones[pose_bone.name] = [pose_bone, False, False, False] # [PoseBone, LocKey, RotKey, ScaleKey] for each bone on the current frame
				frame_bones[pose_bone.name][index + 1] = True # Enable the corresponding keyframe type for that bone on this frame

	# Set the frame_count to the the REAL number of frames in the action if there is only 1
	if len(frames) == 1:
		anim.header.frameCount = 1

	# Step 2: Gathering Animation Data
	progress.enter_substeps(len(frames))
	
	for frame, bones in frames.items():
		context.scene.frame_set(frame) # Set frame directly

		for name, bone_info in bones.items():
			anim_bone = anim_bones[name]
			pose_bone = bone_info[0] # the first element in the bone_info array is the PoseBone

			if bone_info[1] == True:
				loc = get_loc_vec(pose_bone, self.anim_type) * 2.54 # Remove the multiplication later
				key = SEAnim.KeyFrame(frame - frame_start, (loc.x, loc.y, loc.z))
				anim_bone.posKeys.append(key)

			if bone_info[2] == True:
				quat = get_rot_quat(pose_bone, self.anim_type)
				key = SEAnim.KeyFrame(frame - frame_start, (quat.x, quat.y, quat.z, quat.w))
				anim_bone.rotKeys.append(key)
			
			# Scale Isn't Supported Yet
			if bone_info[3] == True:
				do="nothing"

		progress.step()

	context.scene.frame_set(frame_original)
	progress.leave_substeps()

	# Step 3: Finalizing Data
	for name, bone in anim_bones.items():
		anim.bones.append(bone)

	for pose_marker in action.pose_markers:
		note = SEAnim.Note()
		note.frame = pose_marker.frame
		note.name = pose_marker.name
		anim.notes.append(note)

	# Step 4: Writing File
	anim.save(filepath)

	# DEBUG - Verify that the written file is valid
	#SEAnim.LOG_ANIM_HEADER = True
	#SEAnim.Anim(filepath)

def save(self, context):
	ob = bpy.context.object
	if ob.type != 'ARMATURE':
		return {'CANCELLED'}

	prefix = self.prefix #os.path.basename(self.filepath)
	suffix = self.suffix
	path = os.path.dirname(self.filepath) + "\\"

	filepath = self.filepath # Gets automatically updated per-action if self.use_actions is true, otherwise it stays the same

	with ProgressReport(context.window_manager) as progress:
		actions = []
		if self.use_actions:
			actions = bpy.data.actions
		else:
			actions = [bpy.context.object.animation_data.action]

		progress.enter_substeps(len(actions))
		
		for action in actions:
			if self.use_actions:
				filepath = path + prefix + action.name + suffix + ".seanim"

			progress.enter_substeps(1, action.name)
			try:
				export_action(self, context, progress, action, filepath)
			except Exception as e:
				progress.leave_substeps("ERROR: " + repr(e))
			else:
				progress.leave_substeps()

		progress.leave_substeps()

	return {'FINISHED'}
