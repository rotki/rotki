import type { APIRequestContext, Page } from '@playwright/test';
import { backendUrl } from '../../../playwright.config';
import { fulfillJson, installFakeTasks } from './fake-tasks';

export interface FakeBankConnection {
  identifier?: string;
  connector?: string;
  bankCode?: string;
  name: string;
  lastSyncTs?: number;
  lastError?: string;
  /** The TAN prompt of a challenge the connection is waiting on. */
  pendingTan?: string;
  /** The bank rejected or expired the last TAN. */
  authExpired?: boolean;
}

type StoredBankConnection = FakeBankConnection & { identifier: string };

export interface FakeBankSetup {
  connections: FakeBankConnection[];
  /**
   * The USD amount the first connection holds; the other connections hold nothing, so the bank
   * total equals it.
   *
   * @remarks
   * Served as USD with `value === amount`. The e2e profile's main currency is USD, so the stored value
   * is already the priced value; a balance in another currency would carry a value the price refresh
   * later rewrites, and totals read before and after that refresh would disagree for no app reason.
   */
  usdBalance: string;
  /** Connection names whose sync task fails, with the message the backend would report. */
  failingSyncs?: Record<string, string>;
  /**
   * Connection names whose sync the bank pauses for a TAN, with the TAN prompt.
   *
   * @remarks
   * The backend ends such a sync with no result and no message, and reports the challenge only on the
   * connection's sync status, so both are faked here.
   */
  pausedSyncs?: Record<string, string>;
  /**
   * Makes adding a connection fail the way the backend does when Qonto rejects the key.
   *
   * @remarks
   * `setup_bank` answers a failed key validation with 409 and a plain message, never with a
   * per-slot field error, so that is the only rejection shape faked here.
   */
  rejectCredentials?: string;
}

export interface BankRequests {
  added: Record<string, unknown>[];
  authenticated: Record<string, unknown>[];
  edited: Record<string, unknown>[];
  removed: Record<string, unknown>[];
  synced: Record<string, unknown>[];
}

export interface BankEventSeed {
  groupIdentifier: string;
  timestamp: number;
  eventType: string;
  eventSubtype: string;
  asset: string;
  amount: string;
  connectionName: string;
  notes?: string;
  extraData?: { bank_account_id: string; kind: string; reference?: string; counterparty_account?: string };
}

/** Whether a request body addresses the connection, as the backend does: by connection identifier. */
function isAddressed(connection: StoredBankConnection, body: Record<string, unknown>): boolean {
  return body.identifier === connection.identifier;
}

/** The initial identifier of a fake connection; it stays unchanged when the connection is renamed. */
export function fakeBankIdentifier(name: string): string {
  return `fake-${name.toLowerCase().replaceAll(' ', '-')}`;
}

function toWireConnection(connection: StoredBankConnection): Record<string, unknown> {
  const connector = connection.connector ?? 'qonto';
  return {
    bank_code: connection.bankCode ?? null,
    connector,
    display_name: connector === 'fints' ? 'FinTS/HBCI' : 'Qonto',
    identifier: connection.identifier,
    name: connection.name,
    sync_status: {
      auth_challenge: connection.pendingTan
        ? {
            challenge: connection.pendingTan,
            challenge_data: null,
            challenge_html: null,
            challenge_mime_type: null,
            primitive: 'otp input',
            prompt: connection.pendingTan,
          }
        : null,
      auth_expired: connection.authExpired ?? false,
      last_error: connection.lastError ?? null,
      last_sync_ts: connection.lastSyncTs ?? null,
      running: false,
    },
  };
}

/**
 * Adds a bank transaction event through the real backend.
 *
 * @remarks
 * The backend accepts the bank entry type on `PUT /history/events`, so bank events need no faking: the
 * history view, the edit form and accounting all read real rows.
 */
export async function apiAddBankEvent(request: APIRequestContext, event: BankEventSeed): Promise<number> {
  const response = await request.put(`${backendUrl}/api/1/history/events`, {
    data: {
      amount: event.amount,
      asset: event.asset,
      entry_type: 'bank transaction event',
      event_subtype: event.eventSubtype,
      event_type: event.eventType,
      extra_data: event.extraData ?? null,
      group_identifier: event.groupIdentifier,
      location: 'banks',
      location_label: event.connectionName,
      sequence_index: 0,
      timestamp: event.timestamp,
      user_notes: event.notes ?? null,
    },
    failOnStatusCode: false,
  });

  const body = await response.json();
  if (!response.ok())
    throw new Error(`failed to add bank event ${event.groupIdentifier}: ${JSON.stringify(body)}`);

  return body.result.identifier;
}

/**
 * Stands in for a Qonto account on the `/banks` endpoints, and records what the app sends.
 *
 * @remarks
 * Install before navigating: a route only applies to requests made after it exists. Balance queries and
 * syncs are async tasks, answered through {@link installFakeTasks}. `/banks/supported` is left to
 * the real backend, which serves the Qonto manifest without an account.
 */
export async function fakeBankEndpoints(page: Page, setup: FakeBankSetup): Promise<BankRequests> {
  const requests: BankRequests = { added: [], authenticated: [], edited: [], removed: [], synced: [] };
  let connections: StoredBankConnection[] = setup.connections.map(connection => ({
    ...connection,
    identifier: connection.identifier ?? fakeBankIdentifier(connection.name),
  }));
  const { start: startTask } = await installFakeTasks(page);

  await page.route('**/api/1/banks', async (route) => {
    const request = route.request();
    const method = request.method();
    if (method === 'GET') {
      await fulfillJson(route, connections.map(toWireConnection));
      return;
    }

    const body = request.postDataJSON() ?? {};
    if (method === 'PUT') {
      requests.added.push(body);
      if (setup.rejectCredentials) {
        await route.fulfill({
          body: JSON.stringify({ message: setup.rejectCredentials, result: null }),
          contentType: 'application/json',
          status: 409,
        });
        return;
      }
      const name = String(body.name);
      const identifier = fakeBankIdentifier(name);
      connections = [...connections, {
        bankCode: body.credentials?.bank_code,
        connector: body.connector,
        identifier,
        name,
      }];
      await fulfillJson(route, { history_start_ts: null, identifier, success: true });
      return;
    }
    else if (method === 'PATCH') {
      requests.edited.push(body);
      if (body.new_name)
        connections = connections.map(connection => isAddressed(connection, body) ? { ...connection, name: String(body.new_name) } : connection);
    }
    else if (method === 'DELETE') {
      requests.removed.push(body);
      connections = connections.filter(connection => !isAddressed(connection, body));
    }
    await fulfillJson(route, true);
  });

  await page.route('**/api/1/banks/sync', async (route) => {
    const body = route.request().postDataJSON() ?? {};
    requests.synced.push(body);
    const name = connections.find(connection => isAddressed(connection, body))?.name ?? '';
    const pausedTan = setup.pausedSyncs?.[name];
    if (pausedTan) {
      connections = connections.map(connection => connection.name === name ? { ...connection, pendingTan: pausedTan } : connection);
      await fulfillJson(route, { task_id: startTask(null) });
      return;
    }
    const failure = setup.failingSyncs?.[name];
    await fulfillJson(route, { task_id: failure ? startTask(null, failure) : startTask(true) });
  });

  await page.route('**/api/1/banks/auth', async (route) => {
    const body = route.request().postDataJSON() ?? {};
    requests.authenticated.push(body);
    if (Object.keys(body).some(key => !['identifier', 'response'].includes(key))) {
      await route.fulfill({
        body: JSON.stringify({ message: JSON.stringify({ unknown: ['Unknown field.'] }), result: null }),
        contentType: 'application/json',
        status: 400,
      });
      return;
    }
    connections = connections.map(connection => isAddressed(connection, body) ? { ...connection, pendingTan: undefined } : connection);
    await fulfillJson(route, true);
  });

  await page.route('**/api/1/banks/balances**', async (route) => {
    const params = new URL(route.request().url()).searchParams;
    const identifier = params.get('identifier');
    const connector = params.get('connector');
    const holder = connections[0]?.identifier;
    const balance = { USD: { amount: setup.usdBalance, value: setup.usdBalance } };
    const queried = connections
      .filter(connection => (!identifier || connection.identifier === identifier) && (!connector || (connection.connector ?? 'qonto') === connector))
      .map(connection => ({
        accounts: connection.identifier === holder
          ? [{
              amount: setup.usdBalance,
              asset: 'USD',
              iban: 'DE02120300000000202051',
              identifier: `${connection.identifier}-checking`,
              name: 'Business checking',
              value: setup.usdBalance,
            }]
          : [],
        balances: connection.identifier === holder ? balance : {},
        connector: connection.connector ?? 'qonto',
        identifier: connection.identifier,
        name: connection.name,
      }));
    await fulfillJson(route, {
      task_id: startTask({
        aggregate: queried.some(connection => connection.identifier === holder) ? balance : {},
        connections: queried,
      }),
    });
  });

  return requests;
}
