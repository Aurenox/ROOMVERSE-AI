"use client";

import {useEffect, useRef, useState} from "react";
import {Maximize2, Minus, Plus, RotateCcw, X} from "lucide-react";

const tiles = ["greenhouse", "library", "observatory", "station", "hotel", "vault", "submarine", "museum", "loop"];

export function SceneViewer({scene, title, imageSource}: {scene: string; title: string; imageSource?: string}) {
  const container = useRef<HTMLDivElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const points = useRef(new Map<number, {x:number; y:number}>());
  const scaleRef = useRef(1);
  const [scale,setScale] = useState(1);
  const [expanded,setExpanded] = useState(false);
  useEffect(() => {
    if (!expanded) return;
    const previous=document.activeElement as HTMLElement | null;
    const overflow=document.body.style.overflow;
    document.body.style.overflow="hidden";
    container.current?.querySelector<HTMLButtonElement>('[aria-label="Close expanded scene"]')?.focus();
    const keys=(event:KeyboardEvent)=>{
      if(event.key==="Escape"){event.preventDefault();setExpanded(false);}
      if(event.key==="Tab"){
        const items=Array.from(container.current?.querySelectorAll<HTMLElement>('button:not(:disabled),[tabindex="0"]') || []);
        const first=items[0],last=items[items.length-1];
        if(event.shiftKey && document.activeElement===first){event.preventDefault();last?.focus();}
        else if(!event.shiftKey && document.activeElement===last){event.preventDefault();first?.focus();}
      }
    };
    document.addEventListener("keydown",keys);
    return()=>{document.body.style.overflow=overflow;document.removeEventListener("keydown",keys);previous?.focus();};
  },[expanded]);
  const tile = imageSource ? -1 : tiles.indexOf(scene);

  function zoom(next: number, x?: number, y?: number) {
    const box = viewport.current;
    if (!box) return;
    const bounded = Math.min(5,Math.max(1,next));
    const anchorX = x ?? box.clientWidth / 2;
    const anchorY = y ?? box.clientHeight / 2;
    const ratio = bounded / scaleRef.current;
    const left = (box.scrollLeft + anchorX) * ratio - anchorX;
    const top = (box.scrollTop + anchorY) * ratio - anchorY;
    scaleRef.current = bounded;
    setScale(bounded);
    requestAnimationFrame(() => {box.scrollLeft = left; box.scrollTop = top;});
  }

  return <div ref={container} role={expanded ? "dialog" : undefined} aria-modal={expanded || undefined} aria-label={expanded ? `${title} enlarged image` : undefined} className={expanded ? "scene-viewer expanded-scene" : "scene-viewer"}>
    <div className="scene-tools">
      <button className="icon-button" aria-label="Zoom out" disabled={scale <= 1} onClick={() => zoom(scale / 1.4)}><Minus size={17}/></button>
      <output aria-label="Scene zoom">{Math.round(scale*100)}%</output>
      <button className="icon-button" aria-label="Zoom in" disabled={scale >= 5} onClick={() => zoom(scale * 1.4)}><Plus size={17}/></button>
      <button className="icon-button" aria-label="Reset scene zoom" onClick={() => zoom(1)}><RotateCcw size={17}/></button>
      <button className="icon-button" aria-label={expanded ? "Close expanded scene" : "Expand scene"} aria-pressed={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? <><X size={20}/><span>Close</span></> : <Maximize2 size={17}/>}</button>
    </div>
    <div ref={viewport} className="scene-viewport" tabIndex={0} aria-label="Scene image. Drag to pan, pinch to zoom, or use arrow keys and zoom buttons."
      onKeyDown={e => {
        const box = viewport.current!;
        const directions: Record<string,[number,number]> = {ArrowLeft:[-80,0],ArrowRight:[80,0],ArrowUp:[0,-80],ArrowDown:[0,80]};
        if (directions[e.key]) {e.preventDefault(); box.scrollBy(...directions[e.key]);}
        if (e.key === "+" || e.key === "=") {e.preventDefault(); zoom(scale*1.4);}
        if (e.key === "-") {e.preventDefault(); zoom(scale/1.4);}
        if (e.key === "Escape") setExpanded(false);
      }}
      onPointerDown={e => {
        if (e.button !== 0) return;
        e.currentTarget.setPointerCapture(e.pointerId);
        points.current.set(e.pointerId,{x:e.clientX,y:e.clientY});
      }}
      onPointerMove={e => {
        const previous = points.current.get(e.pointerId);
        if (!previous) return;
        const before = [...points.current.values()];
        points.current.set(e.pointerId,{x:e.clientX,y:e.clientY});
        const after = [...points.current.values()];
        if (after.length === 2) {
          const distance = (pair: typeof after) => Math.hypot(pair[0].x-pair[1].x,pair[0].y-pair[1].y);
          const rect = e.currentTarget.getBoundingClientRect();
          const oldDistance = distance(before);
          if (oldDistance > 0) zoom(scaleRef.current * distance(after)/oldDistance,
            (after[0].x+after[1].x)/2-rect.left,(after[0].y+after[1].y)/2-rect.top);
        } else {
          e.currentTarget.scrollLeft -= e.clientX-previous.x;
          e.currentTarget.scrollTop -= e.clientY-previous.y;
        }
      }}
      onPointerUp={e => points.current.delete(e.pointerId)}
      onPointerCancel={e => points.current.delete(e.pointerId)}
      onLostPointerCapture={e => points.current.delete(e.pointerId)}>
      <div className="scene-surface" role="img" aria-label={title}
        style={{width:`${scale*100}%`,height:`${scale*100}%`,
          backgroundImage:`url(${imageSource || (tile < 0 ? "/art/midnight-original.png" : "/art/scene-sheet-original.png")})`,
          backgroundSize:tile < 0 ? "contain" : "300% 300%",
          backgroundPosition:tile < 0 ? "center" : `${tile%3*50}% ${Math.floor(tile/3)*50}%`}}/>
    </div>
    <p className="muted">Drag to inspect any corner · Pinch or use + to zoom</p>
  </div>;
}
