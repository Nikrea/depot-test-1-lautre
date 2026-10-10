"""Étape 5 bis (secours) : exporte la timeline en FCPXML, à importer dans Resolve.

    python pipeline/to_fcpxml.py D:/Projets/MaVideo

Puis dans Resolve : Fichier > Importer > Timeline… > _derush/timeline.fcpxml
Marche aussi avec la version gratuite, sans scripting.
"""
import argparse
import sys
from fractions import Fraction
from pathlib import Path
from xml.sax.saxutils import quoteattr

sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, probe, project_paths  # noqa: E402


def frame_dur(fps):
    """24 -> 1/24 ; 23.976 -> 1001/24000."""
    if abs(fps - round(fps)) > 0.01:
        return Fraction(1001, round(fps * 1001 / 1000) * 1000)
    return Fraction(1, round(fps))


def t(seconds):
    f = Fraction(seconds)
    return "0s" if f == 0 else f"{f.numerator}/{f.denominator}s"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projet")
    ap.add_argument("--resolution", default="1920x1080")
    ap.add_argument("--no-broll", action="store_true")
    args = ap.parse_args()

    paths = project_paths(args.projet)
    edl = load_json(paths["edl"])
    fd = frame_dur(edl["fps"])
    w, h = args.resolution.lower().split("x")
    placements, clips = [], {}
    if not args.no_broll and paths["placements"].exists():
        placements = load_json(paths["placements"])["placements"]
        clips = {c["id"]: c for c in load_json(paths["index"])["clips"]}

    formats = {}  # (frameDuration, w, h) -> id

    def fmt(fdur, fw, fh):
        key = (fdur, fw, fh)
        if key not in formats:
            formats[key] = f"f{len(formats) + 1}"
        return formats[key]

    seq_fmt = fmt(fd, int(w), int(h))
    assets = []  # lignes XML

    def asset(aid, path, info):
        attrs = [f'id="{aid}"', f"name={quoteattr(Path(path).stem)}", 'start="0s"']
        if info["is_image"]:
            attrs += ['duration="0s"', 'hasVideo="1"',
                      f'format="{fmt(None, info["width"], info["height"])}"']
        else:
            attrs.append(f'duration="{t(Fraction(round(info["duration"] * 1000), 1000))}"')
            if info["has_video"]:
                vfd = frame_dur(info["fps"]) if info["fps"] else fd
                attrs += ['hasVideo="1"', f'format="{fmt(vfd, info["width"], info["height"])}"']
            if info["has_audio"]:
                attrs += ['hasAudio="1"', 'audioSources="1"',
                          f'audioChannels="{info["audio_channels"]}"', f'audioRate="{info["audio_rate"]}"']
        uri = Path(path).resolve().as_uri()
        assets.append(f'    <asset {" ".join(attrs)}>\n'
                      f'      <media-rep kind="original-media" src={quoteattr(uri)}/>\n    </asset>')

    voice_info = probe(edl["source"])
    asset("a0", edl["source"], voice_info)
    ids = {}
    for p in placements:
        c = clips.get(p["broll"])
        if c and c["id"] not in ids:
            ids[c["id"]] = f"a{len(ids) + 1}"
            asset(ids[c["id"]], c["path"], probe(c["path"]))

    # Chaque B-roll est accroché (lane 1) au morceau de voix sous lequel il commence.
    segs = edl["segments"]
    hooked = {i: [] for i in range(len(segs))}
    for p in placements:
        if p["broll"] not in ids:
            continue
        k = next((i for i, s in enumerate(segs) if s["rec_in"] <= p["rec_in"] < s["rec_out"]), len(segs) - 1)
        hooked[k].append(p)

    spine = []
    for i, s in enumerate(segs):
        start, off, dur = s["src_in"] * fd, s["rec_in"] * fd, (s["src_out"] - s["src_in"]) * fd
        inner = []
        for p in hooked[i]:
            c = clips[p["broll"]]
            boff = start + (p["rec_in"] - s["rec_in"]) * fd
            bdur = (p["rec_out"] - p["rec_in"]) * fd
            tag = "video" if c["type"] == "image" else "asset-clip"
            bstart = Fraction(round(p["src_in_s"] * 1000), 1000) / fd
            bstart = round(bstart) * fd  # aligné sur une image
            inner.append(f'          <{tag} ref="{ids[p["broll"]]}" lane="1" offset="{t(boff)}" '
                         f'start="{t(bstart)}" duration="{t(bdur)}" name={quoteattr(Path(c["path"]).stem)}'
                         + (' srcEnable="video"/>' if tag == "asset-clip" else '/>'))
        body = ("\n" + "\n".join(inner) + "\n        ") if inner else ""
        spine.append(f'        <asset-clip ref="a0" offset="{t(off)}" start="{t(start)}" '
                     f'duration="{t(dur)}" name={quoteattr(Path(edl["source"]).stem)}>'
                     f'{body}</asset-clip>')

    fmt_lines = []
    for (fdur, fw, fh), fid in formats.items():
        rate = f' frameDuration="{t(fdur)}"' if fdur else ""
        name = "FFVideoFormatRateUndefined" if fdur is None else f"FFVideoFormat{fh}p{round(1 / fdur)}"
        fmt_lines.append(f'    <format id="{fid}" name="{name}"{rate} width="{fw}" height="{fh}"/>')

    total = edl["duration_frames"] * fd
    name = f"{paths['root'].name} - derush"
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
  <resources>
{chr(10).join(fmt_lines)}
{chr(10).join(assets)}
  </resources>
  <library>
    <event name={quoteattr(name)}>
      <project name={quoteattr(name)}>
        <sequence format="{seq_fmt}" duration="{t(total)}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
          <spine>
{chr(10).join(spine)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
'''
    paths["fcpxml"].write_text(xml, encoding="utf-8")
    print(f"[OK] {paths['fcpxml']}\n     Resolve : Fichier > Importer > Timeline… "
          f"(projet réglé à {edl['fps']:g} i/s AVANT l'import)")


if __name__ == "__main__":
    main()
