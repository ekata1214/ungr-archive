# SPDX-License-Identifier: MIT
"""単一カット／全カットのビルド＋レンダー入口。

使い方:
  blender -b ~/Desktop/sho-lin-soccer.blend \\
    -P /workspace/blender/scenes/build_part_field.py -- \\
    --cut 01 --render-cut

  blender ... -- --cuts-all --render-cut
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Dict, List, Tuple

# ensure scenes/ on path
_SCENES = Path(__file__).resolve().parents[1]
if str(_SCENES) not in sys.path:
    sys.path.insert(0, str(_SCENES))

from cuts.catalog import CATALOG, by_id  # noqa: E402
from cuts.common import (  # noqa: E402
    ART_DIR,
    RENDER_DIR,
    artifact_url,
    render_cut_video,
    save_cut_blend,
    still_qc,
)


def _all_builders() -> Dict[str, callable]:
    from cuts.norway import BUILDERS as N  # noqa: E402
    from cuts.spain import BUILDERS as S  # noqa: E402
    from cuts.france import BUILDERS as F  # noqa: E402
    from cuts.argentina import BUILDERS as A  # noqa: E402
    from cuts.extras import BUILDERS as E  # noqa: E402

    out: Dict[str, callable] = {}
    out.update(N)
    out.update(S)
    out.update(F)
    out.update(A)
    out.update(E)
    return out


def parse_cut_ids(argv: List[str]) -> List[str]:
    if "--cuts-all" in argv:
        return [c[0] for c in CATALOG]
    ids: List[str] = []
    if "--cut" in argv:
        i = argv.index("--cut")
        if i + 1 < len(argv):
            raw = argv[i + 1]
            for part in raw.replace(",", " ").split():
                ids.append(part.zfill(2))
    return ids


def run_one(cut_id: str, do_render: bool) -> Tuple[str, int, Path | None]:
    builders = _all_builders()
    meta = by_id()
    if cut_id not in builders:
        raise KeyError(f"No builder for cut {cut_id}")
    slug, instr, block = meta[cut_id]
    print(f"\n=== CUT {cut_id} [{block}] {slug} ===")
    print(instr)
    frames = builders[cut_id]()
    print(f"Built {frames}f")
    # mid still for QC
    mid = max(1, frames // 2)
    still_qc(slug, mid, "mid")
    save_cut_blend(slug)
    art = None
    if do_render:
        art = render_cut_video(slug, frames)
        print(f"URL: {artifact_url(art.name)}")
    return slug, frames, art


def write_index(results: List[Tuple[str, str, str, str]]) -> Path:
    """results: (cut_id, slug, instruction, url_or_pending)"""
    ART_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# 37カット 出力一覧", ""]
    for cut_id, slug, instr, url in results:
        lines.append(f"## {int(cut_id)}. {instr}")
        lines.append("")
        if url:
            lines.append(url)
        else:
            lines.append(f"(pending) `{slug}.mp4`")
        lines.append("")
    out = ART_DIR / "CUTS_INDEX.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    (RENDER_DIR / "CUTS_INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    return out


def main_from_argv(argv: List[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv
    ids = parse_cut_ids(argv)
    if not ids:
        print("No --cut / --cuts-all specified")
        return
    do_render = "--render-cut" in argv or "--render-cuts" in argv
    results: List[Tuple[str, str, str, str]] = []
    meta = by_id()
    for cut_id in ids:
        slug, instr, _block = meta[cut_id]
        try:
            _slug, _frames, art = run_one(cut_id, do_render)
            url = artifact_url(art.name) if art else ""
            results.append((cut_id, slug, instr, url))
        except Exception as e:
            traceback.print_exc()
            results.append((cut_id, slug, instr, f"ERROR: {e}"))
    write_index(results)
    print("Done. Index:", ART_DIR / "CUTS_INDEX.md")


if __name__ == "__main__":
    main_from_argv()
