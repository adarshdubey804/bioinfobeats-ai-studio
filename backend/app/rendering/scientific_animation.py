"""Create short, deterministic scientific motion-graphic clips with Pillow and FFmpeg."""
from __future__ import annotations
import math, re, subprocess, uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from app.core.config import settings

W,H,FPS,SECONDS=960,540,24,5
BG=(11,20,32); CYAN=(72,215,208); MINT=(157,244,207); WHITE=(237,245,246); MUTED=(141,164,178); PANEL=(20,43,56)

def _font(size):
    candidates=["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/dejavu/DejaVuSans.ttf"]
    for path in candidates:
        if Path(path).is_file(): return ImageFont.truetype(path,size)
    return ImageFont.load_default()

def _base(title,frame):
    im=Image.new("RGB",(W,H),BG);d=ImageDraw.Draw(im)
    d.text((42,26),str(title)[:72],font=_font(27),fill=MINT)
    d.text((42,H-32),"BIOINFOBEATS  •  SCIENTIFIC MOTION GRAPHIC  •  SCHEMATIC",font=_font(13),fill=MUTED)
    return im,d

def _dna(d,t):
    for i in range(28):
        y=105+i*13
        phase=i*.42+t*2.4
        x1=390+100*math.sin(phase);x2=570-100*math.sin(phase)
        d.line((x1,y,x2,y),fill=(49,91,115),width=3)
        d.ellipse((x1-5,y-5,x1+5,y+5),fill=CYAN)
        d.ellipse((x2-5,y-5,x2+5,y+5),fill=MINT)

def _central(d,t):
    labels=[("DNA",150),("RNA",480),("PROTEIN",810)]
    for label,x in labels:
        d.rounded_rectangle((x-95,205,x+95,285),radius=18,fill=PANEL,outline=CYAN,width=3)
        box=d.textbbox((0,0),label,font=_font(25));d.text((x-(box[2]-box[0])/2,230),label,font=_font(25),fill=WHITE)
    d.line((250,245,380,245),fill=MINT,width=5);d.line((580,245,710,245),fill=MINT,width=5)
    # moving information particles
    for start in (250,580):
        x=start+130*((t*1.4)%1)
        d.ellipse((x-8,237,x+8,253),fill=MINT)

def _pathway(d,t,payload):
    nodes=payload.get("nodes") or [{"id":"A","label":"Signal"},{"id":"B","label":"Kinase"},{"id":"C","label":"Response"}]
    edges=payload.get("edges") or [{"from":"A","to":"B"},{"from":"B","to":"C"}]
    if not 2<=len(nodes)<=10 or len(edges)>20: raise ValueError("Animation supports 2–10 pathway nodes and up to 20 edges.")
    ids=[str(n.get("id","")) for n in nodes]
    if len(set(ids))!=len(ids) or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,24}",v) for v in ids): raise ValueError("Pathway node IDs must be unique simple identifiers.")
    pos={str(n["id"]):(130+(i%5)*175,190+(i//5)*170) for i,n in enumerate(nodes)}
    for e in edges:
        if e.get("from") not in pos or e.get("to") not in pos: raise ValueError("Pathway edge references an unknown node.")
        a,b=pos[e["from"]],pos[e["to"]];d.line((a[0]+48,a[1],b[0]-48,b[1]),fill=(65,120,137),width=4)
        x=a[0]+(b[0]-a[0])*((t*1.5)%1);y=a[1]+(b[1]-a[1])*((t*1.5)%1)
        d.ellipse((x-7,y-7,x+7,y+7),fill=MINT)
    for node in nodes:
        x,y=pos[str(node["id"])]
        d.rounded_rectangle((x-58,y-34,x+58,y+34),radius=13,fill=PANEL,outline=CYAN,width=3)
        label=str(node.get("label",node["id"]))[:15];box=d.textbbox((0,0),label,font=_font(15))
        d.text((x-(box[2]-box[0])/2,y-10),label,font=_font(15),fill=WHITE)

def _alignment(d,t,payload):
    seq=payload.get("sequences") or ["ATGCTAGCTA","ATG-TAGCTA"]
    if not 2<=len(seq)<=6: raise ValueError("Alignment animation supports 2–6 sequences.")
    seq=[re.sub(r"\s+","",str(s).upper()) for s in seq]
    if len({len(s) for s in seq})!=1 or len(seq[0])>50 or any(not re.fullmatch(r"[ACGTUNRYKMSWBDHVX-]+",s) for s in seq): raise ValueError("Sequences must be equal-length supported aligned strings (maximum 50 columns).")
    active=int((t*len(seq[0]))%len(seq[0]))
    for row,s in enumerate(seq):
        d.text((85,150+row*58),"SEQ "+str(row+1),font=_font(17),fill=MUTED)
        for col,char in enumerate(s):
            x=220+col*14;y=135+row*58
            fill=CYAN if col==active else (34,63,73)
            d.rounded_rectangle((x,y,x+13,y+34),radius=2,fill=fill)
            d.text((x+1,y+7),char,font=_font(14),fill=BG if col==active else WHITE)

def _phylogeny(d,t,payload):
    labels=payload.get("labels") or ["Human","Mouse","Bird","Fish"]
    if not 2<=len(labels)<=8 or any(not str(x).strip() or len(str(x))>30 for x in labels): raise ValueError("Phylogeny animation supports 2–8 short labels.")
    top=125; gap=300/(len(labels)-1);ys=[top+i*gap for i in range(len(labels))]
    d.line((250,ys[0],250,ys[-1]),fill=CYAN,width=4)
    d.line((130,(ys[0]+ys[-1])/2,250,(ys[0]+ys[-1])/2),fill=CYAN,width=4)
    progress=min(1,max(0,t*1.5))
    for i,(label,y) in enumerate(zip(labels,ys)):
        end=250+440*progress
        d.line((250,y,end,y),fill=MINT,width=4)
        if progress>.2: d.ellipse((end-6,y-6,end+6,y+6),fill=CYAN)
        d.text((710,y-12),str(label),font=_font(18),fill=WHITE)

def create_animation(kind,payload):
    title=str(payload.get("title") or kind.replace("_"," ").title())[:90]
    media=(Path(settings.media_storage_dir).resolve()/"public").resolve();folder=(media/"scientific-animations").resolve();folder.mkdir(parents=True,exist_ok=True)
    job=uuid.uuid4().hex;frames=folder/job;frames.mkdir()
    total=FPS*SECONDS
    draw_fn={"dna":_dna,"central_dogma":_central,"pathway":lambda d,t:_pathway(d,t,payload),"alignment":lambda d,t:_alignment(d,t,payload),"phylogeny":lambda d,t:_phylogeny(d,t,payload)}.get(kind)
    if draw_fn is None: raise ValueError("Unsupported animation kind.")
    try:
        for i in range(total):
            im,d=_base(title,i);draw_fn(d,i/total)
            im.save(frames/f"frame-{i:04}.png",optimize=False)
        output=folder/(job+".mp4")
        subprocess.run([settings.ffmpeg_binary,"-y","-framerate",str(FPS),"-i",str(frames/"frame-%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(output)],check=True,capture_output=True,text=True,timeout=180)
        return {"kind":kind,"title":title,"url":"/media/scientific-animations/"+output.name,"duration_seconds":SECONDS,"fps":FPS,"width":W,"height":H,"format":"mp4","disclaimer":"Educational schematic animation; not a molecular simulation or an inferred biological result."}
    finally:
        for p in frames.glob("*.png"): p.unlink(missing_ok=True)
        frames.rmdir()
