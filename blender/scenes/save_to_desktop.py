"""Build the news-CG scene and save as .blend on Desktop."""
import bpy
from pathlib import Path

script = Path(__file__).with_name("shaolin_soccer_haaland_gk_news_cg.py")
ns = {"__name__": "shaolin_soccer_haaland_gk_news_cg"}
exec(script.read_text(encoding="utf-8"), ns)
ns["build_scene"]()

out = Path.home() / "Desktop" / "shaolin_soccer_haaland_gk_news_cg.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(out))
print(f"Saved: {out}")
