"""List objects/collections in the active .blend (for mapping)."""
import bpy

print("=== FILE ===", bpy.data.filepath or "(unsaved)")
print("=== COLLECTIONS ===")
for col in bpy.data.collections:
    objs = [o.name for o in col.objects]
    print(f"  {col.name}: {objs}")

print("=== ALL OBJECTS ===")
for obj in bpy.data.objects:
    parent = obj.parent.name if obj.parent else "-"
    kind = obj.type
    mats = []
    if hasattr(obj.data, "materials"):
        mats = [m.name for m in obj.data.materials if m]
    print(f"  {obj.name} | type={kind} | parent={parent} | mats={mats}")

print("=== ARMATURES ===")
for arm in bpy.data.armatures:
  print(f"  {arm.name} bones={[b.name for b in arm.bones]}")
