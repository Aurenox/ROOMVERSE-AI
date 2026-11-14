"use client";

import {useEffect, useRef, useState} from "react";

type Point = {x:number;y:number};
type Box = {x:number;y:number;width:number;height:number};

export function PhotoPrivacy({file,apply,close}: {file:File;apply:(file:File)=>void;close:()=>void}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const anchor = useRef<Point | null>(null);
  const undo = useRef<ImageData[]>([]);
  const active = useRef(true);
  const [ready,setReady] = useState(false);
  const [size,setSize] = useState({width:1,height:1});
  const [count,setCount] = useState(0);
  const [box,setBox] = useState<Box>();
  const [error,setError] = useState("");
  const [busy,setBusy] = useState(false);
  useEffect(() => {
    active.current = true;
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      if (!active.current || !canvas.current) return;
      const ratio = Math.min(1,1280 / Math.max(image.width,image.height));
      canvas.current.width = Math.round(image.width*ratio); canvas.current.height = Math.round(image.height*ratio);
      canvas.current.getContext("2d")?.drawImage(image,0,0,canvas.current.width,canvas.current.height);
      setSize({width:canvas.current.width,height:canvas.current.height});
      setReady(true);
    };
    image.onerror = () => {if (active.current) setError("This photo could not be opened. Choose another JPEG, PNG, or WebP.");};
    image.src = url;
    return () => {active.current = false;URL.revokeObjectURL(url);};
  }, [file]);
  function point(event:React.PointerEvent<HTMLCanvasElement>) {
    const target = event.currentTarget;
    const bounds = target.getBoundingClientRect();
    return {x:Math.max(0,Math.min(target.width,(event.clientX-bounds.left)*target.width/bounds.width)),y:Math.max(0,Math.min(target.height,(event.clientY-bounds.top)*target.height/bounds.height))};
  }
  function rectangle(end:Point): Box {
    const start = anchor.current!;
    return {x:Math.min(start.x,end.x),y:Math.min(start.y,end.y),width:Math.abs(start.x-end.x),height:Math.abs(start.y-end.y)};
  }
  return <section className="privacy-editor" aria-label="Cover private details">
    <h3>Cover private details before upload</h3>
    <p>Drag over each sensitive area to cover it with solid black. Cover the whole face, number, email, or document, including its edges. These edits happen on your device.</p>
    <div className="privacy-canvas-wrap">
      <canvas ref={canvas} aria-label="Photo editor. Drag rectangles over private details." onPointerDown={event => {if (!ready || busy || event.button !== 0) return;if (undo.current.length >= 12) {setError("Apply these covers before adding more, or undo a cover first.");return;}event.currentTarget.setPointerCapture(event.pointerId);anchor.current=point(event);}} onPointerMove={event => {if (anchor.current) setBox(rectangle(point(event)));}} onPointerUp={event => {
        if (!anchor.current) return;
        const area = rectangle(point(event)); anchor.current = null; setBox(undefined);
        const context = canvas.current?.getContext("2d");
        if (!context || area.width < 4 || area.height < 4) return;
        undo.current.push(context.getImageData(0,0,canvas.current!.width,canvas.current!.height));
        context.fillStyle="#000";context.fillRect(Math.floor(area.x),Math.floor(area.y),Math.ceil(area.width)+1,Math.ceil(area.height)+1);
        setCount(undo.current.length);
      }} onPointerCancel={() => {anchor.current=null;setBox(undefined);}}/>
      {box && <div className="privacy-selection" style={{left:`${box.x/size.width*100}%`,top:`${box.y/size.height*100}%`,width:`${box.width/size.width*100}%`,height:`${box.height/size.height*100}%`}}/>}
    </div>
    <p className="muted">If you cannot cover an area precisely, use a different photo. Automated screening is not a guarantee.</p>
    <div className="actions"><button className="button primary" type="button" disabled={!ready || !count || busy} onClick={() => {
      setBusy(true);
      canvas.current?.toBlob(blob => {if (!active.current) return;setBusy(false);if (blob) apply(new File([blob],"room-private.jpg",{type:"image/jpeg"}));else setError("Could not save the covered photo. Please try again.");},"image/jpeg",0.92);
    }}>{busy ? "Saving…" : "Use covered photo"}</button><button type="button" className="button outline" disabled={!count || busy} onClick={() => {const previous=undo.current.pop();if (previous) canvas.current?.getContext("2d")?.putImageData(previous,0,0);setCount(undo.current.length);}}>Undo last cover</button><button className="text-button" type="button" onClick={close}>Cancel edits</button></div>
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
