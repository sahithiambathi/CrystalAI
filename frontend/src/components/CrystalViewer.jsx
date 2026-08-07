import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const ELEMENT_COLORS = {
  H: "#dbeafe",
  C: "#475569",
  N: "#38bdf8",
  O: "#f97316",
  Ba: "#8b5cf6",
};

function colorForElement(element) {
  return ELEMENT_COLORS[element] ?? "#14b8a6";
}

export default function CrystalViewer({ crystal }) {
  const mountRef = useRef(null);
  const uniqueElements = Array.from(
    new Set((crystal?.atoms ?? []).map((atom) => atom.element)),
  ).sort();

  useEffect(() => {
    if (!mountRef.current || !crystal) {
      return undefined;
    }

    const mount = mountRef.current;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("transparent");

    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(10, 10, 14);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    scene.add(new THREE.AmbientLight("#ffffff", 1.2));
    const directionalLight = new THREE.DirectionalLight("#c7d2fe", 2.2);
    directionalLight.position.set(10, 14, 8);
    scene.add(directionalLight);

    const crystalGroup = new THREE.Group();
    scene.add(crystalGroup);

    crystal.atoms.forEach((atom) => {
      const material = new THREE.MeshPhysicalMaterial({
        color: colorForElement(atom.element),
        roughness: 0.15,
        metalness: 0.08,
        clearcoat: 0.8,
      });
      const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.45, 32, 32), material);
      sphere.position.set(atom.x, atom.y, atom.z);
      crystalGroup.add(sphere);
    });

    crystal.bonds.forEach((bond) => {
      const start = crystal.atoms[bond.start];
      const end = crystal.atoms[bond.end];
      const direction = new THREE.Vector3(end.x - start.x, end.y - start.y, end.z - start.z);
      const midpoint = new THREE.Vector3(
        (start.x + end.x) / 2,
        (start.y + end.y) / 2,
        (start.z + end.z) / 2,
      );

      const bondGeometry = new THREE.CylinderGeometry(0.08, 0.08, direction.length(), 14);
      const bondMaterial = new THREE.MeshStandardMaterial({
        color: "#94a3b8",
        emissive: "#1e293b",
      });
      const cylinder = new THREE.Mesh(bondGeometry, bondMaterial);
      cylinder.position.copy(midpoint);
      cylinder.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        direction.clone().normalize(),
      );
      crystalGroup.add(cylinder);
    });

    const box = new THREE.Box3().setFromObject(crystalGroup);
    const center = box.getCenter(new THREE.Vector3());
    crystalGroup.position.sub(center);

    let animationFrameId = 0;
    const animate = () => {
      crystalGroup.rotation.y += 0.002;
      controls.update();
      renderer.render(scene, camera);
      animationFrameId = window.requestAnimationFrame(animate);
    };
    animationFrameId = window.requestAnimationFrame(animate);

    const resizeObserver = new ResizeObserver(() => {
      const nextWidth = mount.clientWidth;
      const nextHeight = mount.clientHeight;
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, nextHeight);
    });
    resizeObserver.observe(mount);

    return () => {
      window.cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
      scene.clear();
    };
  }, [crystal]);

  return (
    <div className="viewer-wrap">
      <div className="viewer-canvas" ref={mountRef} />
      {uniqueElements.length > 0 ? (
        <div className="viewer-legend" aria-label="Atom color legend">
          {uniqueElements.map((element) => (
            <span className="viewer-legend-item" key={element}>
              <span
                className="viewer-legend-swatch"
                style={{ backgroundColor: colorForElement(element) }}
                aria-hidden="true"
              />
              {element}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
