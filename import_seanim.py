import bpy
from mathutils import *
from progress_report import ProgressReport, ProgressReportSubstep
import os
from . import seanim as SEAnim

g_scale = 1 / 2.54 # This is the scale multiplier for exported anims - currently this is only here to ensure compatibility with Blender-CoD 

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
	anim = SEAnim.Anim(filepath)

	# Import the animation data
	ob = bpy.context.object

	bpy.ops.object.mode_set(mode='POSE')

	actionName = os.path.basename(os.path.splitext(filepath)[0])
	action = bpy.data.actions.new(actionName)
	ob.animation_data.action = action
	ob.animation_data.action.use_fake_user = True

	scene = bpy.context.scene
	scene.render.fps = anim.header.framerate
	scene.frame_start = 0 #bpy.context.scene.frame_current
	scene.frame_end = scene.frame_start + anim.header.frameCount - 1

	# Import the actual keyframes
	progress.enter_substeps(anim.header.boneCount)

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

			# Import the position keyframes
			if len(tag.posKeys):
				bone.matrix_basis.identity()

				fcurves = [ action.fcurves.new(data_path='pose.bones["%s"].%s' % (tag.name, 'location'), index=index, action_group=tag.name) for index in range(3) ]
				keyCount = len(tag.posKeys)
				for axis, fcurve in enumerate(fcurves):
					fcurve.color_mode='AUTO_RGB'
					fcurve.keyframe_points.add(keyCount + 1) # Add an extra keyframe for the control keyframe
					fcurve.keyframe_points[0].co = Vector((-1, bone.location[axis])) # Add the control keyframe # Can be changed to Vector((-1, 0)) because Location 0,0,0 is rest pos
				
				for k, key in enumerate(tag.posKeys):
					offset = Vector(key.data) * g_scale # Currently the conversion is only here because I never added scaling options for Blender-CoD

					# Viewanims are SEANIM_TYPE_ABSOLUTE - But all children of j_gun has a SEANIM_TYPE_RELATIVE override
					if animType == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE and bone.parent is not None:
						bone.matrix.translation = bone.parent.matrix*offset
					else: # Use DELTA / RELATIVE results (ADDITIVE is unknown)
						bone.matrix_basis.translation = offset

					#bone.keyframe_insert("location", index=-1, frame=key.frame, group=tag.name)
					for axis, fcurve in enumerate(fcurves):
						fcurve.keyframe_points[k + 1].co = Vector((key.frame, bone.location[axis]))
						fcurve.keyframe_points[k + 1].interpolation = 'LINEAR'

				# Update the FCurves
				for fc in fcurves:
					fc.update()

			# Import the rotation keyframes
			if len(tag.rotKeys):
				bone.matrix_basis.identity()

				fcurves = [ action.fcurves.new(data_path='pose.bones["%s"].%s' % (tag.name, 'rotation_quaternion'), index=index, action_group=tag.name) for index in range(4) ]
				keyCount = len(tag.rotKeys)
				for axis, fcurve in enumerate(fcurves):
					fcurve.color_mode='AUTO_YRGB'
					fcurve.keyframe_points.add(keyCount + 1) # Add an extra keyframe for the control keyframe
					fcurve.keyframe_points[0].co = Vector((-1, [1,0,0,0][axis])) # Add the control keyframe

				for k, key in enumerate(tag.rotKeys):
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

					for axis, fcurve in enumerate(fcurves):
						fcurve.keyframe_points[k + 1].co = Vector((key.frame, bone.rotation_quaternion[axis])) #bone.rotation_quaternion[axis]
						fcurve.keyframe_points[k + 1].interpolation = 'LINEAR'

				# Update the FCurves
				for fc in fcurves:
					fc.update()
			
			bone.keyframe_delete(data_path="location", frame=scene.frame_start-1, group=tag.name)
			bone.keyframe_delete(data_path="rotation_quaternion", frame=scene.frame_start-1, group=tag.name)

			# Remove any leftover temporary transformations for this bone
			bone.matrix_basis.identity()

		progress.step()
	progress.leave_substeps()

	# Notetracks
	for note in anim.notes:
		notetrack = ob.animation_data.action.pose_markers.new(note.name)
		notetrack.frame = note.frame

	bpy.context.scene.update()
	bpy.ops.object.mode_set(mode='POSE')

	return {'FINISHED'}
