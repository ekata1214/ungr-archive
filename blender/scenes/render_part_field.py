"""フィールドのみをレンダー（俯瞰）"""
import bpy
from pathlib import Path

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720

# フィールド全体が見えるカメラ
cam_data = bpy.data.cameras.new("FieldCam")
cam = bpy.data.objects.new("FieldCam", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (0, 0, 95)
cam.rotation_euler = (0, 0, 0)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = 120

if not bpy.data.objects.get("Key"):
    light = bpy.data.lights.new("Key", "SUN")
    obj = bpy.data.objects.new("Key", light)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (0.8, 0.2, 0.5)

out = Path("/workspace/blender/renders/parts/field_only.png")
out.parent.mkdir(parents=True, exist_ok=True)
scene.frame_set(1)
scene.render.filepath = str(out)
bpy.ops.render.render(write_still=True)
print(f"Rendered: {out}")
