"use client";

import { useEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export function SceneOrbit({ target, zoom }: { target: [number, number, number]; zoom: number }) {
  const { camera, gl, invalidate } = useThree();
  const controls = useRef<OrbitControls | null>(null);
  const previousZoom = useRef(1);
  useEffect(() => {
    const orbit = new OrbitControls(camera, gl.domElement);
    orbit.target.set(...target);
    orbit.minDistance = 0.4;
    orbit.maxDistance = 30;
    orbit.enablePan = true;
    orbit.update();
    const onChange = () => invalidate();
    orbit.addEventListener("change", onChange);
    controls.current = orbit;
    previousZoom.current = 1;
    return () => { orbit.removeEventListener("change", onChange); orbit.dispose(); controls.current = null; };
  }, [camera, gl, invalidate, target]);
  useEffect(() => {
    if (!controls.current) return;
    camera.position.sub(controls.current.target).multiplyScalar(zoom / previousZoom.current).add(controls.current.target);
    previousZoom.current = zoom;
    controls.current.update();
    invalidate();
  }, [camera, invalidate, zoom, target]);
  return null;
}
