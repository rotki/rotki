import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { useBanksApi } from '@/modules/banks/use-banks-api';

const backendUrl = process.env.VITE_BACKEND_URL;

const wireManifest = {
  access_tier: 'official api',
  auth_flow: [{ primitive: 'static secret' }],
  capabilities: ['balances', 'transactions'],
  display_name: 'Qonto',
  docs_url: 'https://docs.qonto.com',
  location: 'qonto',
  maintainer: 'rotki',
  secrets: [{ description: 'The organization login', label: 'Login', slot: 'api_key' }],
  setup_notes: ['Only one key per organization'],
  version: '1.0.0',
};

describe('useBanksApi', () => {
  it('should parse the supported bank manifests', async () => {
    server.use(http.get(`${backendUrl}/api/1/banks/supported`, () => HttpResponse.json({ message: '', result: [wireManifest] })));

    const [manifest] = await useBanksApi().getSupportedBanks();

    expect(manifest).toMatchObject({ displayName: 'Qonto', docsUrl: 'https://docs.qonto.com', setupNotes: ['Only one key per organization'] });
  });

  it('should parse the bank connections with their sync status', async () => {
    server.use(http.get(`${backendUrl}/api/1/banks`, () => HttpResponse.json({
      message: '',
      result: [{ display_name: 'Qonto', location: 'qonto', name: 'main', sync_status: { last_error: 'boom', last_sync_ts: 10, running: false } }],
    })));

    expect(await useBanksApi().getBanks()).toEqual([{
      displayName: 'Qonto',
      location: 'qonto',
      name: 'main',
      syncStatus: { lastError: 'boom', lastSyncTs: 10, running: false },
    }]);
  });

  it('should add a connection with the credentials keyed by slot', async () => {
    let body: unknown;
    server.use(http.put(`${backendUrl}/api/1/banks`, async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({ message: '', result: true });
    }));

    await useBanksApi().addBank({ credentials: { api_key: 'login', api_secret: 'secret' }, location: 'qonto', name: 'main' });

    expect(body).toEqual({ credentials: { api_key: 'login', api_secret: 'secret' }, location: 'qonto', name: 'main' });
  });

  it('should leave an empty new name out of an edit and send the credentials it is given', async () => {
    let body: unknown;
    server.use(http.patch(`${backendUrl}/api/1/banks`, async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({ message: '', result: true });
    }));

    await useBanksApi().editBank({ credentials: { api_secret: 'new-secret' }, location: 'qonto', name: 'main', newName: '' });

    expect(body).toEqual({ credentials: { api_secret: 'new-secret' }, location: 'qonto', name: 'main' });
  });

  it('should remove a connection by location and name', async () => {
    let body: unknown;
    server.use(http.delete(`${backendUrl}/api/1/banks`, async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({ message: '', result: true });
    }));

    expect(await useBanksApi().removeBank({ location: 'qonto', name: 'main' })).toBe(true);
    expect(body).toEqual({ location: 'qonto', name: 'main' });
  });

  it('should start a sync task for one connection', async () => {
    let body: unknown;
    server.use(http.post(`${backendUrl}/api/1/banks/sync`, async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({ message: '', result: { task_id: 7 } });
    }));

    expect(await useBanksApi().syncBanks({ location: 'qonto', name: 'main' })).toEqual({ taskId: 7 });
    expect(body).toEqual({ async_query: true, location: 'qonto', name: 'main' });
  });

  it('should only ask to bypass the balance cache when told to', async () => {
    const queries: string[] = [];
    server.use(http.get(`${backendUrl}/api/1/banks/balances`, ({ request }) => {
      queries.push(new URL(request.url).search);
      return HttpResponse.json({ message: '', result: { task_id: 8 } });
    }));

    await useBanksApi().queryBankBalances();
    await useBanksApi().queryBankBalances(true);

    expect(queries).toEqual(['?async_query=true', '?async_query=true&ignore_cache=true']);
  });
});
