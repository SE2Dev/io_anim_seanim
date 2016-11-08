import bpy
from mathutils import *
from progress_report import ProgressReport, ProgressReportSubstep
import os
from . import seanim as SEAnim

def save(self, context):
	print("Filepath: " + self.filepath)
	return {'FINISHED'}
