"use client";

import {useCallback, useEffect, useRef, useState} from "react";

export function CameraCapture({capture,close}: {capture:(file:File)=>void;close:()=>void}) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const version = useRef(0);
  const [error,setError] = useState("");
  const [ready,setReady] = useState(false);
  const [busy,setBusy] = useState(false);
  const [devices,setDevices] = useState<MediaDeviceInfo[]>([]);
  const [device,setDevice] = useState("");

  const stop = useCallback(() => {
    version.current++;
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
    if (video.current) video.current.srcObject = null;
  }, []);

  const start = useCallback(async (id?:string) => {
    stop(); setError(""); setReady(false);
    const request = version.current;
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setError("Live camera needs HTTPS or localhost. Use Upload photo or Phone camera app instead."); return;
    }
    try {
      const media = await navigator.mediaDevices.getUserMedia({audio:false,video:id ? {deviceId:{exact:id}} : {facingMode:{ideal:"environment"},width:{ideal:1280},height:{ideal:960}}});
      if (request !== version.current) {media.getTracks().forEach(track => track.stop()); return;}
      stream.current = media;
      if (video.current) {video.current.srcObject = media; await video.current.play();}
      const available = await navigator.mediaDevices.enumerateDevices();
      if (request !== version.current) return;
      setDevices(available.filter(item => item.kind === "videoinput"));
      setDevice(media.getVideoTracks()[0]?.getSettings().deviceId || "");
    } catch (reason) {
      if (request !== version.current) return;
      stop();
      const name = (reason as DOMException).name;
      setError(name === "NotAllowedError" ? "Camera permission was denied. Allow it in your browser, or upload a photo instead." : name === "NotFoundError" ? "No camera was found. Connect a webcam or upload a photo." : "The camera could not start. Close other camera apps and try again, or upload a photo.");
    }
  }, [stop]);

  useEffect(() => {
    const timer = window.setTimeout(() => {void start();},0);
    return () => {window.clearTimeout(timer); stop();};
  }, [start,stop]);

  function takePhoto() {
    const source = video.current;
    if (!source || !source.videoWidth || !source.videoHeight || busy) return;
    setBusy(true);
    const request = version.current;
    const canvas = document.createElement("canvas");
    const ratio = Math.min(1,1280 / Math.max(source.videoWidth,source.videoHeight));
    canvas.width = Math.round(source.videoWidth*ratio); canvas.height = Math.round(source.videoHeight*ratio);
    const context = canvas.getContext("2d");
    if (!context) {setError("Photo capture is unavailable. Upload a photo instead.");setBusy(false);return;}
    context.drawImage(source,0,0,canvas.width,canvas.height);
    canvas.toBlob(blob => {
      if (request !== version.current) return;
      setBusy(false);
      if (!blob) {setError("Could not capture this frame. Please try again.");return;}
      stop(); capture(new File([blob],"room-camera.jpg",{type:"image/jpeg"}));
    },"image/jpeg",0.9);
  }

  return <section className="camera-panel" aria-label="Live camera">
    <h3>Frame objects, not personal information</h3>
    <p className="muted">Live video stays on your device. Avoid yourself, other people, photographs, documents, and readable screens. Capture a still photo, then review it before sending.</p>
    <video ref={video} muted autoPlay playsInline onLoadedData={() => setReady(true)} aria-label="Local camera preview"/>
    {devices.length > 1 && <label>Camera<select value={device} onChange={event => {setDevice(event.target.value);void start(event.target.value);}}>{devices.map((item,index) => <option key={item.deviceId} value={item.deviceId}>{item.label || `Camera ${index+1}`}</option>)}</select></label>}
    {error && <p role="alert" className="error">{error}</p>}
    <div className="actions"><button type="button" className="button primary" disabled={!ready || busy} onClick={takePhoto}>{busy ? "Capturing…" : "Capture photo"}</button><button type="button" className="button outline" onClick={() => {stop();close();}}>Close camera</button>{error && <button type="button" className="text-button" onClick={() => {void start();}}>Retry camera</button>}</div>
  </section>;
}
