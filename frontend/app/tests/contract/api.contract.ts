import { describe, expect, it } from 'vitest';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { contractExpected, contractUsername } from './contract-env';

/**
 * Contract tests (measurement framework §5.1): the frontend's own api
 * composables against a live backend booted on a golden profile. Each call
 * exercises the full client pipeline — URL construction, parameter
 * serialization, snake_case<->camelCase transforms and zod schema parsing —
 * so a passing test means the real frontend understands the real backend.
 * Assertions compare against the profile generator's expected.json, never
 * against hand-written fixtures that could drift.
 */

describe('users api contract', () => {
  it('should list the profile user', async () => {
    const profiles = await useUsersApi().getUserProfiles();
    expect(profiles).toContain(contractUsername());
  });

  it('should report the profile user as logged in', async () => {
    const logged = await useUsersApi().loggedUsers();
    expect(logged).toContain(contractUsername());
  });
});

describe('settings api contract', () => {
  it('should fetch and parse the user settings', async () => {
    const settings = await useSettingsApi().getSettings();
    // camelCase fields with meaningful values prove the response went
    // through the case transform and the UserSettingsModel zod parse
    expect(settings.data.version).toBeGreaterThan(0);
    expect(settings.general.mainCurrency.tickerSymbol).toBeTruthy();
  });
});

describe('blockchain accounts api contract', () => {
  it('should return exactly the seeded ethereum accounts', async () => {
    const accounts = await useBlockchainAccountsApi().queryAccounts('eth');
    const addresses = accounts.map(account => account.address).sort();
    const seeded = [...contractExpected().eth_accounts].sort();
    expect(addresses).toEqual(seeded);
  });
});

describe('history events api contract', () => {
  it('should page through history events with the seeded totals', async () => {
    const expected = contractExpected();
    const result = await useHistoryEventsApi().fetchHistoryEvents({
      aggregateByGroupIds: false,
      ascending: [false],
      limit: 10,
      offset: 0,
      orderByAttributes: ['timestamp'],
    });

    expect(result.entriesTotal).toBe(expected.total_events);
    expect(result.entries.length).toBeGreaterThan(0);
  });
});
