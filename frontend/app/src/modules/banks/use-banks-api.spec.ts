import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { ok } from 'plainfp/result';
import { assert, describe, expect, it } from 'vitest';
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
  secrets: [{ description: 'The organization login', label: 'Login', secret: true, slot: 'api_key' }],
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
      result: [{ display_name: 'Qonto', location: 'qonto', name: 'main', sync_status: { auth_challenge: null, last_error: 'boom', last_sync_ts: 10, running: false } }],
    })));

    expect(await useBanksApi().getBanks()).toEqual([{
      displayName: 'Qonto',
      location: 'qonto',
      name: 'main',
      syncStatus: { authChallenge: null, lastError: 'boom', lastSyncTs: 10, running: false },
    }]);
  });

  it('should add a connection with the credentials keyed by slot', async () => {
    let body: unknown;
    server.use(http.put(`${backendUrl}/api/1/banks`, async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({ message: '', result: { history_start_ts: 1_700_000_000, success: true } });
    }));

    const outcome = await useBanksApi().addBank({ credentials: { api_key: 'login', api_secret: 'secret' }, location: 'qonto', name: 'main' });

    expect(outcome).toEqual(ok({ historyStartTs: 1_700_000_000, success: true }));
    expect(body).toEqual({ credentials: { api_key: 'login', api_secret: 'secret' }, location: 'qonto', name: 'main' });
  });

  it('should leave an empty new name out of an edit and send the credentials it is given', async () => {
    let body: unknown;
    server.use(http.patch(`${backendUrl}/api/1/banks`, async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({ message: '', result: true });
    }));

    const outcome = await useBanksApi().editBank({ credentials: { api_secret: 'new-secret' }, location: 'qonto', name: 'main', newName: '' });

    expect(outcome).toEqual(ok(true));
    expect(body).toEqual({ credentials: { api_secret: 'new-secret' }, location: 'qonto', name: 'main' });
  });

  describe('a refused add', () => {
    const payload = { credentials: { api_key: 'login', api_secret: 'secret' }, location: 'qonto', name: 'main' };

    function refuseAdd(status: number, message: string): void {
      server.use(http.put(`${backendUrl}/api/1/banks`, () => HttpResponse.json({ message, result: null }, { status })));
    }

    it('should key a credential error by its slot and a payload field error by the field', async () => {
      refuseAdd(400, JSON.stringify({ api_secret: ['wrong'], name: ['taken'] }));

      const outcome = await useBanksApi().addBank(payload);

      assert(!outcome.ok);
      expect(outcome.error).toEqual({ errors: { api_secret: ['wrong'], name: ['taken'] }, type: 'fields' });
    });

    it.each([
      ['a plain 400 message', 400, 'Qonto rejected the credentials', 'Qonto rejected the credentials'],
      ['a 400 naming no field of the payload', 400, JSON.stringify({ organization: ['unknown'] }), 'unknown'],
      ['a 409 conflict', 409, 'A connection named main already exists', 'A connection named main already exists'],
      ['a server error', 500, 'boom', 'boom'],
    ])('should report %s as a rejection of the whole request', async (_case, status, message, expected) => {
      refuseAdd(status, message);

      const outcome = await useBanksApi().addBank(payload);

      assert(!outcome.ok);
      expect(outcome.error).toEqual({ message: expected, type: 'rejected' });
    });
  });

  it('should classify a refused edit against the credentials the edit sent', async () => {
    server.use(http.patch(`${backendUrl}/api/1/banks`, () => HttpResponse.json(
      { message: JSON.stringify({ api_key: ['required'], api_secret: ['wrong'] }), result: null },
      { status: 400 },
    )));

    const outcome = await useBanksApi().editBank({ credentials: { api_secret: 'new-secret' }, location: 'qonto', name: 'main' });

    assert(!outcome.ok);
    expect(outcome.error).toEqual({ message: 'required', type: 'rejected' });
  });

  describe('answering an authentication request', () => {
    const wireChallenge = {
      challenge: 'Enter the TAN',
      challenge_data: null,
      challenge_html: null,
      challenge_mime_type: null,
      primitive: 'otp input',
      prompt: 'Enter the TAN',
    };

    function answerWith(status: number, result: unknown, bodies: unknown[]): void {
      server.use(http.post(`${backendUrl}/api/1/banks/auth`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ message: '', result }, { status });
      }));
    }

    it('should send only the connection identity and the response', async () => {
      const bodies: unknown[] = [];
      answerWith(200, true, bodies);

      const outcome = await useBanksApi().answerAuthentication({ location: 'fints', name: 'main', response: '123456' });

      expect(outcome).toEqual(ok(true));
      expect(bodies).toEqual([{ location: 'fints', name: 'main', response: '123456' }]);
    });

    it('should hand back the next challenge when the bank asks again', async () => {
      answerWith(202, { ...wireChallenge, primitive: 'app approval poll' }, []);

      const outcome = await useBanksApi().answerAuthentication({ location: 'fints', name: 'main' });

      assert(outcome.ok);
      expect(outcome.value).toMatchObject({ challengeData: null, primitive: 'app approval poll', prompt: 'Enter the TAN' });
    });

    it('should hand back a completed setup with its history start', async () => {
      answerWith(200, { history_start_ts: 1_700_000_000, success: true }, []);

      expect(await useBanksApi().answerAuthentication({ location: 'fints', name: 'main', response: '1' }))
        .toEqual(ok({ historyStartTs: 1_700_000_000, success: true }));
    });

    it('should report a refused answer as a rejection', async () => {
      server.use(http.post(`${backendUrl}/api/1/banks/auth`, () => HttpResponse.json(
        { message: 'The TAN was rejected by the bank', result: null },
        { status: 409 },
      )));

      const outcome = await useBanksApi().answerAuthentication({ location: 'fints', name: 'main', response: '1' });

      assert(!outcome.ok);
      expect(outcome.error).toEqual({ message: 'The TAN was rejected by the bank', type: 'rejected' });
    });
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
