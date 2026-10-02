"use client";

import { useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { SceneOrbit } from "./scene-orbit";

const origin: [number, number, number] = [0, 0, 0];

export default function CartonPreview({ lengthMm, widthMm, heightMm, label, rotateLabel, zoomInLabel, zoomOutLabel, interactionHint }: { lengthMm: number; widthMm: number; heightMm: number; label: string; rotateLabel: string; zoomInLabel: string; zoomOutLabel: string; interactionHint: string }) {
  const [webgl, setWebgl] = useState(false);
  const [angle, setAngle] = useState(0);
  const [zoom, setZoom] = useState(1);
  useEffect(() => { const canvas = document.createElement("canvas"); setWebgl(Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"))); }, []);
  const largest = Math.max(lengthMm, widthMm, heightMm, 1);
  const dimensions: [number, number, number] = [lengthMm / largest, heightMm / largest, widthMm / largest];
  return <div className="rounded-lg border bg-neutral-50 p-3 dark:bg-neutral-900"><div className="h-[420px] overflow-hidden rounded-md" role="img" aria-label={label}>{webgl ? <Canvas frameloop="demand" camera={{ position: [1.5, 1.2, 1.7], fov: 45 }}><SceneOrbit target={origin} zoom={zoom} /><ambientLight intensity={1.5} /><directionalLight position={[2, 3, 3]} intensity={2} /><group rotation={[0, angle, 0]}><mesh><boxGeometry args={dimensions} /><meshStandardMaterial color="#a3b8b1" roughness={1} /></mesh><mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, dimensions[1] / 2 + 0.003, 0]}><planeGeometry args={[dimensions[0], dimensions[2]]} /><meshStandardMaterial color="#5b756d" roughness={1} /></mesh></group></Canvas> : <div className="grid h-full place-items-center text-6xl text-neutral-400" aria-hidden="true">□</div>}</div><div className="mt-3 flex flex-wrap items-center justify-between gap-2"><span className="text-xs text-muted">{lengthMm} × {widthMm} × {heightMm} mm · {interactionHint}</span>{webgl && <div className="flex gap-2"><button className="rounded border px-3 py-1 text-xs" onClick={() => setZoom((value) => Math.max(0.4, value * 0.8))} aria-label={zoomInLabel}>+</button><button className="rounded border px-3 py-1 text-xs" onClick={() => setZoom((value) => Math.min(3, value * 1.25))} aria-label={zoomOutLabel}>−</button><button className="rounded border px-2 py-1 text-xs" onClick={() => setAngle((value) => value + Math.PI / 2)}>{rotateLabel}</button></div>}</div></div>;
}
