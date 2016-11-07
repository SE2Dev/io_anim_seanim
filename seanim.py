import time
import struct

LOG_READ_TIME=False
LOG_ANIM_HEADER=False
LOG_ANIM_BONES=False
LOG_ANIM_BONE_MODIFIERS=False
LOG_ANIM_NOTES=False

def enum(**enums):
    return type('Enum', (), enums)

SEANIM_TYPE = enum(
	SEANIM_TYPE_ABSOLUTE	= 0,
	SEANIM_TYPE_ADDITIVE	= 1,
	SEANIM_TYPE_RELATIVE	= 2,
	SEANIM_TYPE_DELTA		= 3)

SEANIM_PRESENCE_FLAGS = enum(
	# These describe what type of keyframe data is present for the bones
	SEANIM_BONE_LOC		= 1 << 0,
	SEANIM_BONE_ROT		= 1 << 1,
	SEANIM_BONE_SCALE	= 1 << 2,
	# If any of the above flags are set, then bone keyframe data is present, thus this comparing against this mask will return true
	SEANIM_PRESENCE_BONE	=  1 << 0 |  1 << 1  | 1 << 2,
	SEANIM_PRESENCE_NOTE	= 1 << 6, # The file contains notetrack data
	SEANIM_PRESENCE_CUSTOM	= 1 << 7, # The file contains a custom data block
	)


SEANIM_PROPERTY_FLAGS = enum(
	SEANIM_PRECISION_HIGH = 1 << 0)

SEANIM_FLAGS = enum(
	SEANIM_LOOPED = 1 << 0)


class Info:
	def __init__(self, file):
		bytes = file.read(8)
		data = struct.unpack('6ch', bytes)
		
		self.magic = b''
		for i in range(6):
			self.magic += data[i]
		
		assert self.magic == b'SEAnim'
		
		self.version = data[6]

class Header:
	def __init__(self, file):
		bytes = file.read(2)
		data = struct.unpack('h', bytes)
		
		headerSize = data[0]
		bytes = file.read(headerSize - 2)
		data = struct.unpack('=6BfII4BI', bytes); # = prefix tell is to ignore C struct packing rules
		
		self.animType = data[0]
		self.animFlags = data[1]
		self.dataPresenceFlags = data[2]
		self.dataPropertyFlags = data[3]
		# reserved = data[4]
		# reserved = data[5]
		self.framerate = data[6]
		self.frameCount = data[7]
		self.boneCount = data[8]
		self.boneAnimModifierCount = data[9]
		# reserved = data[10]
		# reserved = data[11]
		# reserved = data[12]
		self.noteCount = data[13]

"""
	The Frame_t class is only ever used to get the size and format character used by frame indices in a given sanim file
"""
class Frame_t:
	def __init__(self, header):
		if header.frameCount < 0xFF:
			self.size = 1
			self.char = 'B'
		elif header.frameCount <= 0xFFFF:
			self.size = 2
			self.char = 'h'
		else: #if header.frameCount <= 0xFFFFFFFF:
			self.size = 4
			self.char = 'I'

"""
	The Bone_t class is only ever used to get the size and format character used by frame indices in a given sanim file
"""
class Bone_t:
	def __init__(self, header):
		if header.boneCount < 0xFF:
			self.size = 1
			self.char = 'B'
		elif header.boneCount <= 0xFFFF:
			self.size = 2
			self.char = 'h'
		else: #if header.boneCount <= 0xFFFFFFFF:
			self.size = 4
			self.char = 'I'

"""
	The Precision_t class is only ever used to get the size and format character used by vec3_t, quat_t, etc. in a given sanim file
"""
class Precision_t:
	def __init__(self, header):
		if header.dataPropertyFlags & SEANIM_PROPERTY_FLAGS.SEANIM_PRECISION_HIGH:
			self.size = 8
			self.char = 'd'
		else:
			self.size = 4
			self.char = 'f'

"""
	A small classed used for holding keyframe data 
"""
class KeyFrame:
	def __init__(self, frame, data):
		self.frame = frame
		self.data = data

class Bone:
	def __init__(self, file):
		self.modifier = 0
		self.useModifier = False

		bytes = b''
		for i in range(64):
			b = file.read(1)
			if b == b'\x00':
				self.name = bytes.decode("utf-8")
				break
			bytes += b

		self.locKeyCount = 0
		self.rotKeyCount = 0
		self.scaleKeyCount = 0

		self.posKeys = []
		self.rotKeys = []
		self.scaleKeys = []
			
	def loadData(self, file, frame_t , precision_t, useLoc=False, useRot=False, useScale=False):
		# Read the flags for the bone
		bytes = file.read(1)
		data = struct.unpack("B", bytes)
		self.flags = data[0]
		
		# Load the position keyframes if they are present
		if useLoc:
			bytes = file.read(frame_t.size)
			data = struct.unpack('%c' % frame_t.char, bytes)
			self.locKeyCount = data[0]

			#print("  Reading %d locKeys at 0x%X" % (self.locKeyCount, file.tell() - 1))

			for i in range(self.locKeyCount):
				bytes = file.read(frame_t.size + 3 * precision_t.size)
				data = struct.unpack('=%c3%c' % (frame_t.char, precision_t.char), bytes)

				frame = data[0]
				pos = (data[1], data[2], data[3])

				self.posKeys.append( KeyFrame(frame, pos) )

		# Load the rotation keyframes if they are present
		if useRot:
			bytes = file.read(frame_t.size)
			data = struct.unpack('%c' % frame_t.char, bytes)
			self.rotKeyCount = data[0]

			#print("  Reading %d rotKeys at 0x%X" % (self.rotKeyCount, file.tell() - 1))

			for i in range(self.rotKeyCount):
				#print("    rotKey[%d] at 0x%X" % (i, file.tell()))

				bytes = file.read(frame_t.size + 4 * precision_t.size)
				#print("reading(%d) - actually read(%d)" % (frame_t.size + 4 * precision_t.size, len(bytes)))
				data = struct.unpack('=%c4%c' % (frame_t.char, precision_t.char), bytes)

				frame = data[0]
				quat = (data[1], data[2], data[3], data[4]) #Load the quaternion as XYZW

				self.rotKeys.append( KeyFrame(frame, quat) )

		# Load the Scale Keyrames
		if useScale:
			bytes = file.read(frame_t.size)
			data = struct.unpack('%c' % frame_t.char, bytes)
			self.rotKeyCount = data[0]
			for i in range(self.scaleKeyCount):
				bytes = file.read(frame_t.size + 3 * precision_t.size)
				data = struct.unpack('=%c3%c' % (frame_t.char, precision_t.char), bytes)

				frame = data[0]
				scale = (data[1], data[2], data[3])

				self.scaleKeys.append( KeyFrame(frame, scale) )

class Note:
	def __init__(self, file, frame_t):
		bytes = file.read(frame_t.size)
		data = struct.unpack('%c' % frame_t.char, bytes)
		
		self.frame = data[0]

		bytes = b''
		for i in range(64):
			b = file.read(1)
			if b == b'\x00':
				self.name = bytes.decode("utf-8")
				break
			bytes += b

class Anim:
	def __init__(self, path):
		if LOG_READ_TIME:
			time_start = time.time()

		try:
			file = open(path, "rb")
		except IOError:
			print("Could not open file for reading:\n%s" % path)
			return

		self.info = Info(file)
		self.header = Header(file)
		self.boneAnimModifiers = []

		# Init the frame_t, bone_t and precision_t info
		frame_t = Frame_t(self.header)
		bone_t = Bone_t(self.header)
		precision_t = Precision_t(self.header)

		if LOG_ANIM_HEADER:
			print("Magic: %s" % self.info.magic)
			print("Version: %d" % self.info.version)

			print("AnimType: %d" % self.header.animType)
			print("AnimFlags: %d" % self.header.animFlags)
			print("PresenceFlags: %d" % self.header.dataPresenceFlags)
			print("PropertyFlags: %d" % self.header.dataPropertyFlags)
			print("FrameRate: %f" % self.header.framerate)
			print("frameCount: %d" % self.header.frameCount)
			print("BoneCount: %d" % self.header.boneCount)
			print("NoteCount: %d" % self.header.noteCount)
			print("BoneModifierCount: %d" % self.header.boneAnimModifierCount)

			print("Frame_t Size: %d" % frame_t.size)
			print("Frame_t Char: '%s'" % frame_t.char)

		self.bones = []
		if self.header.dataPresenceFlags & SEANIM_PRESENCE_FLAGS.SEANIM_PRESENCE_BONE:
			useLoc = self.header.dataPresenceFlags & SEANIM_PRESENCE_FLAGS.SEANIM_BONE_LOC
			useRot = self.header.dataPresenceFlags & SEANIM_PRESENCE_FLAGS.SEANIM_BONE_ROT
			useScale = self.header.dataPresenceFlags & SEANIM_PRESENCE_FLAGS.SEANIM_BONE_SCALE

			for i in range(self.header.boneCount):
				if LOG_ANIM_BONES:
					print("Loading Name for Bone[%d]" % i)
				self.bones.append(Bone(file))

			for i in range(self.header.boneAnimModifierCount):
				bytes = file.read(bone_t.size + 1)
				data = struct.unpack("%cB" % bone_t.char, bytes)
				index = data[0]
				self.bones[index].useModifier = True
				self.bones[index].modifier = data[1]

				self.boneAnimModifiers.append(self.bones[index])

				if LOG_ANIM_BONE_MODIFIERS:
					print("Loaded Modifier %d for '%s" % (index, self.bones[index].name))

			for i in range(self.header.boneCount):
				if LOG_ANIM_BONES:
					print("Loading Data For Bone[%d] '%s'" % (i, self.bones[i].name))
				self.bones[i].loadData(file, frame_t, precision_t, useLoc, useRot, useScale)

		self.notes = []
		if self.header.dataPresenceFlags & SEANIM_PRESENCE_FLAGS.SEANIM_PRESENCE_NOTE:
			for i in range(self.header.noteCount):
				note = Note(file, frame_t)
				self.notes.append(note)
				if LOG_ANIM_NOTES:
					print("Loaded Note[%d]:" % i)
					print("  Frame %d: %s" % (note.frame, note.name))

		file.close()

		if LOG_READ_TIME:
			time_end = time.time()
			time_elapsed = time_end - time_start
			print("Done! - Completed in %ss\n" % time_elapsed)

def Read(path):
	return Anim(path)