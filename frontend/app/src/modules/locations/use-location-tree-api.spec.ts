import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { locationImageUrl, useLocationTreeApi } from '@/modules/locations/use-location-tree-api';

const backendUrl = process.env.VITE_BACKEND_URL;

const CUSTOM = 'custom:0b8e/1';
const ENCODED = 'custom%3A0b8e%2F1';

const wireNode = {
  icon: 'lu-landmark',
  identifier: CUSTOM,
  image: null,
  is_active: true,
  is_builtin: false,
  name: 'Harbor',
  parent_identifier: 'exchanges',
};

const node = {
  icon: 'lu-landmark',
  identifier: CUSTOM,
  image: null,
  isActive: true,
  isBuiltin: false,
  name: 'Harbor',
  parentIdentifier: 'exchanges',
};

function reply(result: unknown): Response {
  return HttpResponse.json({ message: '', result });
}

describe('useLocationTreeApi', () => {
  it('should parse the location tree', async () => {
    server.use(http.get(`${backendUrl}/api/1/locations`, () => reply([
      { ...wireNode, identifier: 'total', is_builtin: true, name: 'Total', parent_identifier: null },
      wireNode,
    ])));

    const tree = await useLocationTreeApi().fetchLocationTree();

    expect(tree).toEqual([
      { ...node, identifier: 'total', isBuiltin: true, name: 'Total', parentIdentifier: null },
      node,
    ]);
  });

  it('should reject a tree node missing a field instead of passing it on', async () => {
    const incomplete = Object.fromEntries(Object.entries(wireNode).filter(([key]) => key !== 'is_active'));
    server.use(http.get(`${backendUrl}/api/1/locations`, () => reply([incomplete])));

    await expect(useLocationTreeApi().fetchLocationTree()).rejects.toThrow();
  });

  it('should build an image url that changes with the stored image name', () => {
    const first = locationImageUrl(CUSTOM, 'a.png');
    const second = locationImageUrl(CUSTOM, 'b.png');

    expect(first).toContain(`locations/${ENCODED}/image`);
    expect(first).toContain('v=a.png');
    expect(second).not.toBe(first);
  });
});
