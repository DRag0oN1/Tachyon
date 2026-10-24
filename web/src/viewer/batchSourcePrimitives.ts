import { InstancedMesh, Matrix4, Mesh, SkinnedMesh, type BufferGeometry, type Group } from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// Batch source face primitives within each native part. This retains every
// vertex/normal, material and native component transform; it is not decimation.
export function batchSourcePrimitives(scene: Group): void {
  const original = new Set<BufferGeometry>();
  scene.traverse(object => { if (object instanceof Mesh) original.add(object.geometry); });
  const parents: Group[] = [];
  scene.traverse(object => { if (typeof object.userData.tachyonNativeNodeId === 'string') parents.push(object as Group); });
  const identity = new Matrix4();
  for (const parent of parents) {
    const buckets = new Map<string, Mesh[]>();
    for (const child of parent.children) {
      if (!(child instanceof Mesh) || child instanceof SkinnedMesh || child instanceof InstancedMesh ||
          Array.isArray(child.material) || child.userData.tachyonNativeNodeId !== undefined || Object.keys(child.geometry.morphAttributes).length) continue;
      child.updateMatrix();
      if (!child.matrix.equals(identity)) continue;
      const attributes = Object.keys(child.geometry.attributes).map(name => {
        const a = child.geometry.getAttribute(name);
        return `${name}:${a.itemSize}:${a.normalized}`;
      }).sort().join(',');
      const key = `${child.material.uuid}:${!!child.geometry.index}:${attributes}`;
      const entries = buckets.get(key) ?? []; entries.push(child); buckets.set(key, entries);
    }
    for (const faces of buckets.values()) {
      if (faces.length < 2) continue;
      const geometry = mergeGeometries(faces.map(face => face.geometry), false);
      if (!geometry) continue;
      const mesh = new Mesh(geometry, faces[0].material);
      mesh.name = `${parent.name}_source_surfaces`;
      mesh.userData.tachyonSourcePrimitiveCount = faces.length;
      parent.add(mesh);
      faces.forEach(face => parent.remove(face));
    }
  }
  const retained = new Set<BufferGeometry>();
  scene.traverse(object => { if (object instanceof Mesh) retained.add(object.geometry); });
  original.forEach(geometry => { if (!retained.has(geometry)) geometry.dispose(); });
}
