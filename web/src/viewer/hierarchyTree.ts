import type { NativeNode } from '../api/contracts';

export interface HierarchyItem { node: NativeNode; children: HierarchyItem[]; descendantCount: number }

export function buildNativeHierarchy(nodes: readonly NativeNode[]): HierarchyItem[] {
  const entries = new Map<string, HierarchyItem>();
  nodes.forEach(node => { if (!entries.has(node.id)) entries.set(node.id, { node, children: [], descendantCount: 0 }); });
  const roots: HierarchyItem[] = [];
  entries.forEach(item => {
    let parent = item.node.parentId ? entries.get(item.node.parentId) : undefined;
    const seen = new Set([item.node.id]);
    let ancestor = parent;
    while (ancestor) {
      if (seen.has(ancestor.node.id)) { parent = undefined; break; }
      seen.add(ancestor.node.id);
      ancestor = ancestor.node.parentId ? entries.get(ancestor.node.parentId) : undefined;
    }
    if (parent) parent.children.push(item);
    else roots.push(item);
  });
  const count = (item: HierarchyItem): number => {
    item.descendantCount = item.children.reduce((total, child) => total + count(child) + 1, 0);
    return item.descendantCount;
  };
  roots.forEach(count);
  return roots;
}

export function filterNativeHierarchy(items: HierarchyItem[], query: string): HierarchyItem[] {
  const term = query.trim().toLowerCase();
  if (!term) return items;
  return items.flatMap(item => {
    const children = filterNativeHierarchy(item.children, term);
    return children.length || `${item.node.name} ${item.node.id}`.toLowerCase().includes(term) ? [{ ...item, children }] : [];
  });
}
