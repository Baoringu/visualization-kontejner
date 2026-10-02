"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, ThreeEvent, useThree } from "@react-three/fiber";
import { BoxGeometry, Color, EdgesGeometry, InstancedMesh, Object3D } from "three";
import { useTranslations } from "next-intl";
import type { components } from "../lib/api/schema";
import { boxCenterMeters, boxSizeMeters } from "../lib/coordinates";
import { skuColor } from "../lib/sku-colors";
import { SceneOrbit } from "./scene-orbit";

type Layout = components["schemas"]["LayoutOut"];
type Placement = components["schemas"]["PlacementOut"];
const boxEdges = new EdgesGeometry(new BoxGeometry(1, 1, 1));

function CameraAim({ layout }: { layout: Layout }) {
  const { camera, invalidate } = useThree();
  useEffect(() => {
    const range = Math.max(layout.pallet.length_mm, layout.pallet.width_mm, layout.loaded_height_mm) / 1000;
    const centerX = layout.pallet.length_mm / 2000;
    const centerY = layout.loaded_height_mm / 2000;
    const centerZ = -layout.pallet.width_mm / 2000;
    camera.position.set(centerX + range * 0.9, centerY + range * 0.75, centerZ + range * 0.9);
    camera.lookAt(centerX, centerY, centerZ);
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, invalidate, layout]);
  return null;
}

function Instances({ items, deckHeightMm, selectedId, fallbackSku, onSelect }: { items: Placement[]; deckHeightMm: number; selectedId: string; fallbackSku: string; onSelect: (id: string) => void }) {
  const ref = useRef<InstancedMesh>(null);
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const temp = new Object3D();
    for (let index = 0; index < items.length; index++) {
      temp.position.set(...boxCenterMeters(items[index], deckHeightMm));
      temp.scale.set(...boxSizeMeters(items[index]));
      temp.updateMatrix();
      mesh.setMatrixAt(index, temp.matrix);
      mesh.setColorAt(index, new Color(items[index].instance_id === selectedId ? "#404040" : skuColor(items[index].sku ?? fallbackSku)));
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.computeBoundingSphere();
    invalidate();
  }, [items, deckHeightMm, selectedId, fallbackSku, invalidate]);
  function select(event: ThreeEvent<PointerEvent>) { if (event.instanceId !== undefined) onSelect(items[event.instanceId].instance_id); }
  return <instancedMesh ref={ref} args={[undefined, undefined, items.length]} onPointerDown={select}><boxGeometry args={[1, 1, 1]} /><meshStandardMaterial color="#ffffff" roughness={1} /></instancedMesh>;
}

export default function PalletScene({ layout, palletIndex, selectedId, onSelect, visibleInstanceIds, maxZ }: { layout: Layout; palletIndex: number; selectedId: string; onSelect: (id: string) => void; visibleInstanceIds?: string[]; maxZ?: number }) {
  const t = useTranslations("scene");
  const [zoom, setZoom] = useState(1);
  const visibleSet = useMemo(() => visibleInstanceIds ? new Set(visibleInstanceIds) : null, [visibleInstanceIds]);
  const items = layout.placed.filter((item) => item.pallet_index === palletIndex && (!visibleSet || visibleSet.has(item.instance_id)) && (maxZ === undefined || item.z_mm <= maxZ));
  const deck = layout.pallet;
  const target = useMemo<[number, number, number]>(() => [deck.length_mm / 2000, layout.loaded_height_mm / 2000, -deck.width_mm / 2000], [deck.length_mm, deck.width_mm, layout.loaded_height_mm]);
  return <div className="rounded-md border"><div className="h-[520px] w-full overflow-hidden" role="img" aria-label={t("pallet3d", { number: palletIndex + 1 })}><Canvas frameloop="demand" camera={{ position: [2.1, 1.7, 1.8], fov: 50 }}><CameraAim layout={layout} /><SceneOrbit target={target} zoom={zoom} /><ambientLight intensity={1.4} /><directionalLight position={[2, 4, 3]} intensity={2} /><mesh position={[deck.length_mm / 2000, deck.deck_height_mm / 2000, -deck.width_mm / 2000]} scale={[deck.length_mm / 1000, deck.deck_height_mm / 1000, deck.width_mm / 1000]}><boxGeometry args={[1, 1, 1]} /><meshStandardMaterial color="#737373" /></mesh><Instances items={items} deckHeightMm={deck.deck_height_mm} selectedId={selectedId} fallbackSku={layout.carton?.sku ?? ""} onSelect={onSelect} />{items.map((item) => <lineSegments key={item.instance_id} geometry={boxEdges} dispose={null} position={boxCenterMeters(item, deck.deck_height_mm)} scale={boxSizeMeters(item)}><lineBasicMaterial color="#4b5563" transparent opacity={0.55} /></lineSegments>)}</Canvas></div><div className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2 text-xs"><span className="text-muted">{t("orbitHint")}</span><div className="flex gap-2"><button className="rounded border px-3 py-1" aria-label={t("zoomIn")} onClick={() => setZoom((value) => Math.max(0.4, value * 0.8))}>+</button><button className="rounded border px-3 py-1" aria-label={t("zoomOut")} onClick={() => setZoom((value) => Math.min(3, value * 1.25))}>−</button></div></div></div>;
}
