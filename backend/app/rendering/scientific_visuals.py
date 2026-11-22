"""Deterministic, editable scientific visual asset generation."""
from __future__ import annotations
import html, json, re, uuid
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from app.core.config import settings

NAVY="#0b1420"; CYAN="#48d7d0"; MINT="#9df4cf"; WHITE="#edf5f6"; MUTED="#8da4b2"

def _svg(title:str,width:int=1200,height:int=680):
    root=Element("svg",{"xmlns":"http://www.w3.org/2000/svg","width":str(width),"height":str(height),"viewBox":f"0 0 {width} {height}"})
    SubElement(root,"rect",{"width":"100%","height":"100%","fill":NAVY})
    SubElement(root,"text",{"x":"54","y":"62","fill":MINT,"font-size":"28","font-family":"Arial","font-weight":"bold"}).text=title[:100]
    return root

def _text(root,x,y,value,size=18,color=WHITE,anchor="middle"):
    SubElement(root,"text",{"x":str(x),"y":str(y),"fill":color,"font-size":str(size),"font-family":"Arial","text-anchor":anchor}).text=value[:90]

def _line(root,x1,y1,x2,y2,color=CYAN,width=3):
    SubElement(root,"line",{"x1":str(x1),"y1":str(y1),"x2":str(x2),"y2":str(y2),"stroke":color,"stroke-width":str(width),"stroke-linecap":"round"})

def _circle(root,x,y,r,fill=CYAN):
    SubElement(root,"circle",{"cx":str(x),"cy":str(y),"r":str(r),"fill":fill,"stroke":WHITE,"stroke-width":"1.5"})

def dna(title):
    root=_svg(title or "DNA double helix")
    for i in range(23):
        y=110+i*23
        import math
        x1=390+115*math.sin(i*.48); x2=810-115*math.sin(i*.48)
        _line(root,x1,y,x2,y,"#355b73",2)
        _circle(root,x1,y,6,CYAN);_circle(root,x2,y,6,MINT)
    _text(root,600,635,"Complementary strands · schematic illustration",16,MUTED)
    return root

def pathway(title,nodes,edges):
    if not 2<=len(nodes)<=16 or len(edges)>32: raise ValueError("Pathway requires 2–16 nodes and at most 32 edges.")
    ids=[str(n.get("id","")) for n in nodes]
    if len(set(ids))!=len(ids) or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,24}",v) for v in ids): raise ValueError("Node IDs must be unique simple identifiers.")
    if any(e.get("from") not in ids or e.get("to") not in ids for e in edges): raise ValueError("Every pathway edge must reference an existing node.")
    root=_svg(title or "Molecular pathway")
    pos={}
    for i,node in enumerate(nodes):
        col=i%4; row=i//4;x=180+col*280;y=180+row*190;pos[ids[i]]=(x,y)
    for edge in edges:
        a=pos[edge["from"]];b=pos[edge["to"]];_line(root,a[0]+65,a[1],b[0]-65,b[1],"#4d8794",3)
    for node in nodes:
        x,y=pos[str(node["id"])]
        SubElement(root,"rect",{"x":str(x-92),"y":str(y-38),"width":"184","height":"76","rx":"16","fill":"#142b38","stroke":CYAN,"stroke-width":"2"})
        _text(root,x,y+6,str(node.get("label",node["id"])),16)
    _text(root,600,625,"Conceptual pathway · verify interactions against primary literature",15,MUTED)
    return root

def alignment(title,sequences):
    if not 2<=len(sequences)<=8: raise ValueError("Provide 2–8 aligned sequences.")
    cleaned=[re.sub(r"\s+","",str(s).upper()) for s in sequences]
    if not cleaned or len({len(s) for s in cleaned})!=1 or len(cleaned[0])>100: raise ValueError("Sequences must be equal-length aligned strings (maximum 100 columns).")
    if any(not re.fullmatch(r"[ACGTUNRYKMSWBDHVX-]+",s) for s in cleaned): raise ValueError("Sequence contains unsupported characters.")
    root=_svg(title or "Multiple sequence alignment",max(1200,220+len(cleaned[0])*12),180+len(cleaned)*68)
    for row,seq in enumerate(cleaned):
        _text(root,80,142+row*62,"Seq "+str(row+1),17,MUTED,"start")
        for col,char in enumerate(seq):
            SubElement(root,"rect",{"x":str(210+col*12),"y":str(116+row*62),"width":"12","height":"34","fill":"#163b43" if char!="- " else "#24313a"})
            _text(root,216+col*12,140+row*62,char,16,WHITE)
    return root

def tree(title,labels):
    if not 2<=len(labels)<=12 or any(not str(x).strip() or len(str(x))>45 for x in labels): raise ValueError("Provide 2–12 short taxon labels.")
    root=_svg(title or "Phylogenetic tree")
    x0=180; leafx=850; gap=450/(len(labels)-1)
    ys=[145+i*gap for i in range(len(labels))]
    mid=(ys[0]+ys[-1])/2
    _line(root,x0,mid,400,mid);_line(root,400,ys[0],400,ys[-1])
    for i,(label,y) in enumerate(zip(labels,ys)):
        x=530+(i%3)*80
        _line(root,400,y,x,y);_line(root,x,y,leafx,y)
        _text(root,leafx+20,y+6,str(label)[:45],17,WHITE,"start")
    _text(root,600,635,"Illustrative topology only · branch lengths are not inferred",15,MUTED)
    return root

def generate_visual(kind:str,payload:dict)->dict:
    title=str(payload.get("title") or kind.replace("_"," ").title())
    if kind=="dna": root=dna(title)
    elif kind=="pathway": root=pathway(title,payload.get("nodes",[]),payload.get("edges",[]))
    elif kind=="alignment": root=alignment(title,payload.get("sequences",[]))
    elif kind=="phylogeny": root=tree(title,payload.get("labels",[]))
    else: raise ValueError("Unsupported visual kind.")
    media=Path(settings.media_storage_dir).resolve()
    folder=(media/"scientific-assets").resolve();folder.mkdir(parents=True,exist_ok=True)
    name=uuid.uuid4().hex+".svg";path=folder/name
    path.write_bytes(tostring(root,encoding="utf-8",xml_declaration=True))
    return {"kind":kind,"title":title,"filename":name,"url":"/media/scientific-assets/"+name,"format":"svg","disclaimer":"Generated schematic; validate biological interpretation and references before publication."}
