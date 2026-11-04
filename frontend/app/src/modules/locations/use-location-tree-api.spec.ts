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

interface Captured {
  url?: string;
  body?: unknown;
}

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

  it('should post a new location with a snake-cased body', async () => {
    const captured: Captured = {};
    server.use(http.post(`${backendUrl}/api/1/locations`, async ({ request }) => {
      captured.body = await request.json();
      return reply(wireNode);
    }));

    const created = await useLocationTreeApi().addLocation({ icon: 'lu-landmark', name: 'Harbor', parentIdentifier: 'exchanges' });

    expect(captured.body).toEqual({ icon: 'lu-landmark', name: 'Harbor', parent_identifier: 'exchanges' });
    expect(created).toEqual(node);
  });

  it('should address an edit by the encoded identifier and return both paths', async () => {
    const captured: Captured = {};
    server.use(http.patch(`${backendUrl}/api/1/locations/:identifier`, async ({ request }) => {
      captured.url = request.url;
      captured.body = await request.json();
      return reply({ location: wireNode, new_path: ['Total', 'Banks', 'Harbor'], old_path: ['Total', 'Exchanges', 'Harbor'] });
    }));

    const result = await useLocationTreeApi().editLocation(CUSTOM, { dryRun: true, isActive: false, parentIdentifier: 'banks' });

    expect(captured.url).toBe(`${backendUrl}/api/1/locations/${ENCODED}`);
    expect(captured.body).toEqual({ dry_run: true, is_active: false, parent_identifier: 'banks' });
    expect(result).toEqual({ location: node, newPath: ['Total', 'Banks', 'Harbor'], oldPath: ['Total', 'Exchanges', 'Harbor'] });
  });

  it('should delete a location by the encoded identifier', async () => {
    const captured: Captured = {};
    server.use(http.delete(`${backendUrl}/api/1/locations/:identifier`, ({ request }) => {
      captured.url = request.url;
      return reply(true);
    }));

    expect(await useLocationTreeApi().deleteLocation(CUSTOM)).toBe(true);
    expect(captured.url).toBe(`${backendUrl}/api/1/locations/${ENCODED}`);
  });

  it('should read the usage of a location with its table names camel-cased', async () => {
    const captured: Captured = {};
    server.use(http.get(`${backendUrl}/api/1/locations/:identifier/usage`, ({ request }) => {
      captured.url = request.url;
      return reply({ deletable: false, usage: { children: 1, history_events: 3 } });
    }));

    const usage = await useLocationTreeApi().fetchLocationUsage(CUSTOM);

    expect(captured.url).toBe(`${backendUrl}/api/1/locations/${ENCODED}/usage`);
    expect(usage).toEqual({ deletable: false, usage: { children: 1, historyEvents: 3 } });
  });

  it('should upload an image as multipart form data and return the stored image name', async () => {
    const captured: Captured = {};
    server.use(http.post(`${backendUrl}/api/1/locations/:identifier/image`, async ({ request }) => {
      captured.url = request.url;
      captured.body = (await request.formData()).get('file');
      return reply({ image: 'abc123.png' });
    }));
    const file = new File(['png'], 'logo.png', { type: 'image/png' });

    const image = await useLocationTreeApi().uploadLocationImage(CUSTOM, file);

    expect(image).toBe('abc123.png');
    expect(captured.url).toBe(`${backendUrl}/api/1/locations/${ENCODED}/image`);
    expect(captured.body).toBeInstanceOf(File);
    expect(captured.body).toHaveProperty('name', 'logo.png');
  });

  it('should delete the image of a location', async () => {
    const captured: Captured = {};
    server.use(http.delete(`${backendUrl}/api/1/locations/:identifier/image`, ({ request }) => {
      captured.url = request.url;
      return reply(true);
    }));

    expect(await useLocationTreeApi().deleteLocationImage(CUSTOM)).toBe(true);
    expect(captured.url).toBe(`${backendUrl}/api/1/locations/${ENCODED}/image`);
  });

  it('should build an image url that changes with the stored image name', () => {
    const first = locationImageUrl(CUSTOM, 'a.png');
    const second = locationImageUrl(CUSTOM, 'b.png');

    expect(first).toContain(`locations/${ENCODED}/image`);
    expect(first).toContain('v=a.png');
    expect(second).not.toBe(first);
  });

  it('should read the aliases with their location camel-cased', async () => {
    server.use(http.get(`${backendUrl}/api/1/locations/aliases`, () => reply([{ alias: 'luno', location_identifier: CUSTOM }])));

    expect(await useLocationTreeApi().fetchLocationAliases()).toEqual([{ alias: 'luno', locationIdentifier: CUSTOM }]);
  });

  it('should put an alias with the location snake-cased', async () => {
    const captured: Captured = {};
    server.use(http.put(`${backendUrl}/api/1/locations/aliases`, async ({ request }) => {
      captured.body = await request.json();
      return reply(true);
    }));

    expect(await useLocationTreeApi().setLocationAlias('luno', CUSTOM)).toBe(true);
    expect(captured.body).toEqual({ alias: 'luno', location_identifier: CUSTOM });
  });

  it('should delete an alias by sending it in the body', async () => {
    const captured: Captured = {};
    server.use(http.delete(`${backendUrl}/api/1/locations/aliases`, async ({ request }) => {
      captured.body = await request.json();
      return reply(true);
    }));

    expect(await useLocationTreeApi().deleteLocationAlias('luno')).toBe(true);
    expect(captured.body).toEqual({ alias: 'luno' });
  });
});
