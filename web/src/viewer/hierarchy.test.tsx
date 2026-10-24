import { fireEvent, render, screen, within } from '@testing-library/react';
import { Matrix4 } from 'three';
import { expect, it, vi } from 'vitest';
import type { NativeNode } from '../api/contracts';
import { SourceDetails } from '../panels/ComponentsPanel';
import { componentFixture } from '../test/contracts';
import { NativeHierarchy } from './NativeHierarchy';
import { buildNativeHierarchy, filterNativeHierarchy } from './hierarchyTree';

// Authored metadata only; these labels are not native CAD or validation evidence.
const node = (id: string, name: string, parentId: string | null, hasMesh = false): NativeNode => ({ id, name, parentId, hasMesh, matrix: new Matrix4().toArray() });
const hierarchy = [node('root', 'Reference root', null), node('drive', 'Source drive group', 'root'), node('left', 'Wheel [left].1', 'drive', true), node('right', 'Wheel [right].1', 'drive', true), node('other', 'Other source part', 'root', true)];

it('builds parent relationships from unordered nodes without changing source identities or matrices', () => {
  const input = [hierarchy[2], hierarchy[4], hierarchy[1], hierarchy[0], hierarchy[3]];
  const before = JSON.stringify(input);
  const roots = buildNativeHierarchy(input);
  expect(roots).toHaveLength(1); expect(roots[0].node).toBe(hierarchy[0]);
  expect(roots[0].descendantCount).toBe(4);
  const drive = roots[0].children.find(item => item.node.id === 'drive')!;
  expect(drive.children.map(item => item.node.id)).toEqual(['left', 'right']);
  const filtered = filterNativeHierarchy(roots, ' WHEEL [LEFT] ');
  expect(filtered[0].children.map(item => item.node.id)).toEqual(['drive']);
  expect(filtered[0].children[0].children.map(item => item.node.id)).toEqual(['left']);
  expect(filterNativeHierarchy(roots, 'missing')).toEqual([]);
  expect(JSON.stringify(input)).toBe(before);
});

it('keeps missing-parent and cyclic metadata inspectable without recursive loops', () => {
  const roots = buildNativeHierarchy([node('a', 'A', 'b'), node('b', 'B', 'a'), node('orphan', 'Orphan', 'absent'), node('self', 'Self', 'self')]);
  expect(roots.map(item => item.node.id)).toEqual(['a', 'b', 'orphan', 'self']);
});

it('starts source groups collapsed, selects a collapsed group, and reveals actual parent indentation on expansion', () => {
  const select = vi.fn();
  render(<NativeHierarchy component={{ ...componentFixture, nativeHierarchy: hierarchy }} mode="advanced" disabled={false} onSelect={select} />);
  expect(screen.queryByRole('button', { name: /Wheel \[left\]/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByTitle('Reference root · root'));
  expect(select).toHaveBeenCalledWith('root', 'Reference root');
  fireEvent.click(screen.getByRole('button', { name: 'Expand Reference root' }));
  expect(screen.getByRole('button', { name: 'Expand Source drive group' })).toHaveAttribute('aria-expanded', 'false');
  fireEvent.click(screen.getByRole('button', { name: 'Expand Source drive group' }));
  const left = screen.getByRole('button', { name: /Wheel \[left\]/ });
  expect(left).toHaveAttribute('data-native-node-id', 'left');
  expect(left.closest('ul')?.parentElement?.closest('ul')).not.toBeNull();
  fireEvent.click(left); expect(select).toHaveBeenLastCalledWith('left', 'Wheel [left].1');
  fireEvent.click(screen.getByRole('button', { name: 'Collapse Source drive group' }));
  expect(screen.queryByRole('button', { name: /Wheel \[left\]/ })).not.toBeInTheDocument();
});

it('search reveals matching source nodes with ancestors and restores collapsed state when cleared', () => {
  const select = vi.fn();
  render(<NativeHierarchy component={{ ...componentFixture, nativeHierarchy: hierarchy }} mode="simple" disabled={false} onSelect={select} />);
  const search = screen.getByRole('searchbox', { name: 'Find source parts' });
  fireEvent.change(search, { target: { value: 'wheel [right]' } });
  expect(screen.getByRole('button', { name: /Reference root Source group/ })).toBeVisible();
  const part = screen.getByRole('button', { name: /Wheel \[right\]/ });
  fireEvent.click(part); expect(select).toHaveBeenCalledWith('right', 'Wheel [right].1');
  expect(screen.queryByRole('button', { name: /Wheel \[left\]/ })).not.toBeInTheDocument();
  fireEvent.change(search, { target: { value: 'unmatched' } });
  expect(screen.getByRole('status')).toHaveTextContent('No matching source parts.');
  fireEvent.change(search, { target: { value: '' } });
  expect(screen.getByRole('button', { name: 'Expand Reference root' })).toHaveAttribute('aria-expanded', 'false');
  expect(screen.queryByRole('button', { name: /Wheel \[right\]/ })).not.toBeInTheDocument();
});

it('bounds large flat lists while keeping unavailable sources disabled', () => {
  const nodes = Array.from({ length: 513 }, (_, index) => node(`node-${index}`, `Authored metadata ${index}`, null, true));
  const select = vi.fn();
  render(<NativeHierarchy component={{ ...componentFixture, nativeHierarchy: nodes }} mode="advanced" disabled onSelect={select} />);
  expect(screen.getAllByRole('button', { name: /Source part/ })).toHaveLength(40);
  expect(screen.getByRole('button', { name: /Authored metadata 0 / })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: /Show 40 more source nodes/ }));
  expect(screen.getAllByRole('button', { name: /Source part/ })).toHaveLength(80);
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'node-512' } });
  expect(screen.getAllByRole('button', { name: /Source part/ })).toHaveLength(1);
  expect(select).not.toHaveBeenCalled();
});

it('labels imported reference assemblies and reports aggregate failure without attributing invalid components or inventing zero diagnostics', () => {
  const { rerender } = render(<SourceDetails component={{ ...componentFixture, referenceOnly: true, geometryValidation: { status: 'source_defects', nativeBrepValid: false, invalidComponentInstances: [], invalidDefinitionCount: null, qualifiedForRobotGeneration: false, limitations: ['Aggregate cause has not been located.'] } }} mode="simple" />);
  expect(screen.getByText('Reference assembly · not generated robot')).toBeVisible();
  const warning = screen.getByRole('status');
  expect(warning).toHaveTextContent('Imported reference fails aggregate BRep check');
  expect(warning).toHaveTextContent('original source or aggregate import');
  expect(warning).toHaveTextContent('Aggregate cause has not been located.');
  expect(warning).not.toHaveTextContent(/invalid source component|invalid definitions|0 invalid/);
  rerender(<SourceDetails component={{ ...componentFixture, referenceOnly: true, geometryValidation: { status: 'source_defects', nativeBrepValid: false, invalidComponentInstances: [], invalidDefinitionCount: 0, qualifiedForRobotGeneration: false, limitations: [] } }} mode="advanced" />);
  expect(screen.getByRole('status')).not.toHaveTextContent(/invalid source component|invalid definitions|0 invalid/);
});

it('shows positive diagnostics when supplied and keeps valid native geometry distinct from engineering validation', () => {
  const { rerender } = render(<SourceDetails component={{ ...componentFixture, geometryValidation: { status: 'source_defects', nativeBrepValid: false, invalidComponentInstances: [{ path: '/source/part', name: 'Imported instance', definitionName: 'Imported definition' }], invalidDefinitionCount: 2, qualifiedForRobotGeneration: false, limitations: [] } }} mode="advanced" />);
  expect(within(screen.getByRole('status')).getByText('1 invalid source component instances identified.')).toBeVisible();
  expect(screen.getByRole('status')).toHaveTextContent('2 invalid definitions identified.');
  rerender(<SourceDetails component={{ ...componentFixture, geometryValidation: { status: 'valid', nativeBrepValid: true, invalidComponentInstances: [], invalidDefinitionCount: 0, qualifiedForRobotGeneration: true, limitations: [] } }} mode="simple" />);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  expect(screen.getByText(/not a connected robot assembly/)).toBeVisible();
});
