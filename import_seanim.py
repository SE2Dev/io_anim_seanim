import bpy
from mathutils import *
from progress_report import ProgressReport, ProgressReportSubstep
import os
from . import seanim as SEAnim

# A list (in order of priority) of bone names to automatically search for when determining which bone to use as the root for delta anims
DeltaRootBones = ["tag_origin"]

"""
	Compare two iterable objects, compares each element in 'a' with every element in 'b'
	(Elements in 'a' are prioritized) 
	Returns None if there is no match
"""
def first(a, b):
	for elem in a:
		if elem in b:
			return a
	return None

"""
	Attempt to resolve the animType for a bone based on a given list of modifier bones
	Returns None if no override is needed
"""
def ResolvePotentialAnimTypeOverride(bone, boneAnimModifiers):
	parents = bone.parent_recursive
	if len(parents) == 0 or len(boneAnimModifiers) == 0:
		return None

	for parent in parents:
		for modBone in boneAnimModifiers:
			if parent.name == modBone.name:
				#print("'%s' is (indirect) child of '%s'" % (bone.name, modBone.name))
				return modBone.modifier

	#print("'%s' ~default" % (bone.name))
	return None

def load(self, context, filepath=""):
	ob = bpy.context.object
	if ob.type != 'ARMATURE':
		return {'CANCELLED'}

	path = os.path.dirname(filepath) + "\\"

	try:
		ob.animation_data.action
	except:
		ob.animation_data_create()

	with ProgressReport(context.window_manager) as progress:
		# Begin the progress counter with 1 step for each file
		progress.enter_substeps(len(self.files))

		for f in self.files:
			progress.enter_substeps(1, f.name)
			try:
				load_seanim(self, context, progress, path + f.name)
			except Exception as e:
				progress.leave_substeps("ERROR: " + repr(e))
			else:
				progress.leave_substeps()
		
		# Print when all files have been imported 
		progress.leave_substeps("Finished!")

	return {'FINISHED'}

def load_seanim(self, context, progress, filepath=""):
	anim = SEAnim.Read(filepath)

	# Import the animation data
	ob = bpy.context.object

	bpy.ops.object.mode_set(mode='POSE')

	actionName = os.path.basename(os.path.splitext(filepath)[0])
	ob.animation_data.action = bpy.data.actions.new(actionName)
	ob.animation_data.action.use_fake_user = True

	scene = bpy.context.scene
	scene.render.fps = anim.header.framerate
	scene.frame_start = 0 #bpy.context.scene.frame_current
	scene.frame_end = scene.frame_start + anim.header.frameCount - 1

	# Generate the rest keyframes which are used as a base for the following frames (for *all* bones)
	"""
	for bone in ob.pose.bones.data.bones: #tag in tags:
		try:
			bone.matrix_basis.identity() # Reset to rest pos for the initial keyframe
			bone.keyframe_insert(data_path = "location", index = -1, frame = scene.frame_start)
			bone.keyframe_insert("rotation_quaternion", index = -1, frame = scene.frame_start)
		except:
			pass
	"""

	# Import the actual keyframes
	progress.enter_substeps(anim.header.boneCount, "Adding Keyframes")

	for i, tag in enumerate(anim.bones):
		try:
			# Attempt to resolve the root bone name (if it doesn't have one) based on the prioritized DeltaRootBones array
			if(len(tag.name) == 0 and anim.header.animType == SEAnim.SEANIM_TYPE.SEANIM_TYPE_DELTA):
				root = first(DeltaRootBones, (bone.name for bone in ob.pose.bones.data.bones))
				if root is not None:
					tag.name = root
			bone = ob.pose.bones.data.bones[tag.name]
		except:
			pass
		else:
			animType = ResolvePotentialAnimTypeOverride(bone, anim.boneAnimModifiers)
			if animType is None:
				animType = anim.header.animType
			#else:
			#	print("%s using %d" %( tag.name, animType))

			# Generate the rest keyframes which are used as a base for the following frames (for only the bones that are used)
			try:
				bone.matrix_basis.identity() # Reset to rest pos for the initial keyframe
				bone.keyframe_insert(data_path="location", index=-1, frame=scene.frame_start-1, group=tag.name)
				bone.keyframe_insert(data_path="rotation_quaternion", index=-1, frame=scene.frame_start-1, group=tag.name)
			except:
				pass

			for key in tag.posKeys:
				offset = Vector(key.data) * 1 / 2.54 # Currently the conversion is only here because I never added scaling options for Blender-CoD

				# Viewanims are SEANIM_TYPE_ABSOLUTE - But all children of j_gun has a SEANIM_TYPE_RELATIVE override
				if animType == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE:
					bone.matrix.translation = bone.parent.matrix*offset
				else: # Use DELTA / RELATIVE results (ADDITIVE is unknown)
					bone.matrix_basis.translation = offset

				bone.keyframe_insert("location", index=-1, frame=key.frame, group=tag.name)
			
			for key in tag.rotKeys:
				quat = Quaternion((key.data[3], key.data[0], key.data[1], key.data[2])) # Convert the Quaternion to WXYZ
				angle = quat.to_matrix().to_3x3()

				bone.matrix_basis.identity()
				try:
					bone.parent.matrix
				except:
					# I don't actually remember why this is here - probably to set the root bone(s) to its rest pos / angle
					bone.matrix_basis.identity()
					mat = angle.to_4x4()
				else:
					mat = ( bone.parent.matrix.to_3x3() * angle ).to_4x4()
				
				bone.matrix = mat
			
				bone.keyframe_insert(data_path="rotation_quaternion", index=-1, frame=key.frame, group=tag.name)
			
			bone.keyframe_delete(data_path="location", frame=scene.frame_start-1, group=tag.name)
			bone.keyframe_delete(data_path="rotation_quaternion", frame=scene.frame_start-1, group=tag.name)

		progress.step()
	progress.leave_substeps()

	# Notetracks
	for note in anim.notes:
		notetrack = ob.animation_data.action.pose_markers.new(note.name)
		notetrack.frame = note.frame

	# Force LINEAR interpolation for the imported keyframes (for the current action)
	for fcurve in ob.animation_data.action.fcurves:
		for key in fcurve.keyframe_points:
			key.interpolation = 'LINEAR'

	bpy.context.scene.update()
	bpy.ops.object.mode_set(mode='POSE')

	return {'FINISHED'}
