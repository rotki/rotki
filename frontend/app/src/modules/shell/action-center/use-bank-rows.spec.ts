import type { BankAuthChallenge, BankConnection } from '@/modules/banks/types';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { ActionUrgency } from '@/modules/core/action-center/types';
import { useBankRows } from '@/modules/shell/action-center/use-bank-rows';

const { startOverAuthentication, syncBanks } = vi.hoisted(() => ({
  startOverAuthentication: vi.fn<(connection: BankConnection) => Promise<void>>(),
  syncBanks: vi.fn<(payload?: { identifier?: string }) => Promise<boolean>>(),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: vi.fn(() => ({ startOverAuthentication, syncBanks })),
}));

const challenge: BankAuthChallenge = {
  challenge: 'Enter the TAN',
  challengeData: null,
  challengeHtml: null,
  challengeMimeType: null,
  primitive: 'otp input',
  prompt: 'Enter the TAN',
};

/** A connection with a hex identifier derived from its name, as stable as a real one. */
function identifierOf(name: string): string {
  return Array.from(name, char => char.codePointAt(0)?.toString(16) ?? '').join('');
}

function connection(name: string, syncStatus: Partial<BankConnection['syncStatus']> = {}): BankConnection {
  return {
    connector: 'fints',
    displayName: 'FinTS',
    identifier: identifierOf(name),
    location: 'custom:ing',
    name,
    syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false, ...syncStatus },
  };
}

describe('modules/shell/action-center/use-bank-rows', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    syncBanks.mockResolvedValue(true);
    startOverAuthentication.mockResolvedValue(undefined);
  });

  it('should raise nothing for connections that wait on nothing', () => {
    useBankConnectionsStore().setConnections([connection('Main'), connection('Failing', { lastError: 'boom' })]);

    expect(get(useBankRows())).toEqual([]);
  });

  it('should raise a blocking row per connection waiting on a TAN, leading to its authentication', () => {
    useBankConnectionsStore().setConnections([connection('Main Account', { authChallenge: challenge }), connection('Savings')]);

    const rows = get(useBankRows());

    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      description: 'action_center.rows.integrations.bank_authentication.description::Fints, Main Account',
      id: `bank-authentication-${identifierOf('Main Account')}`,
      target: { kind: 'route', to: { name: '/api-keys/banks/', query: { authenticate: identifierOf('Main Account') } } },
      urgency: ActionUrgency.BLOCKING,
    });
  });

  it('should offer to start over from a TAN the user will not answer', () => {
    useBankConnectionsStore().setConnections([connection('Main', { authChallenge: challenge })]);

    const [row] = get(useBankRows());
    const option = row.options.find(candidate => candidate.id === 'start-over');

    assert(option?.target.kind === 'run');
    option.target.run();
    expect(startOverAuthentication).toHaveBeenCalledExactlyOnceWith(connection('Main', { authChallenge: challenge }));
  });

  it('should give connections whose names slug alike, or not at all, distinct and stable ids from their identifiers', () => {
    const names = ['Main Account', 'main-account', 'Main_Account', 'Конто', '账户'];
    useBankConnectionsStore().setConnections(names.map(name => connection(name, { authChallenge: challenge })));

    const ids = get(useBankRows()).map(row => row.id);

    expect(new Set(ids).size).toBe(names.length);
    expect(ids.every(id => /^[\da-z-]+$/.test(id))).toBe(true);
    expect(get(useBankRows()).map(row => row.id)).toEqual(ids);
  });

  it('should prefer a fresh challenge over an expired one', () => {
    useBankConnectionsStore().setConnections([connection('Main', { authChallenge: challenge, authExpired: true })]);

    expect(get(useBankRows()).map(row => row.urgency)).toEqual([ActionUrgency.BLOCKING]);
  });

  it('should ask to sync again a connection whose TAN expired, as a decision that can wait', () => {
    useBankConnectionsStore().setConnections([connection('Main', { authExpired: true })]);

    const [row] = get(useBankRows());

    expect(row).toMatchObject({
      id: `bank-authentication-expired-${identifierOf('Main')}`,
      snoozable: false,
      urgency: ActionUrgency.DECISION,
    });
    assert(row.target.kind === 'run');
    row.target.run();
    expect(syncBanks).toHaveBeenCalledExactlyOnceWith({ identifier: identifierOf('Main') });
  });

  it('should drop a row as soon as the connections report it answered', () => {
    const store = useBankConnectionsStore();
    store.setConnections([connection('Main', { authChallenge: challenge })]);
    const rows = useBankRows();
    expect(get(rows)).toHaveLength(1);

    store.setConnections([connection('Main')]);

    expect(get(rows)).toEqual([]);
  });
});
