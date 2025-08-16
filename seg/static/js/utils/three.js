/**
 * @param {THREE.Object3D} root
 * @param {THREE.Object3D} current
 */
export function getRecursiveRootNode(root, current) {
  if (current.parent === null || current.parent.uuid === root.uuid) {
    return current;
  }

  let parent = current.parent;
  while (parent.parent.uuid !== root.uuid) {
    parent = parent.parent;
  }

  return parent;
}
