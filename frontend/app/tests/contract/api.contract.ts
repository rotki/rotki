import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { useManualBalancesApi } from '@/modules/balances/api/use-manual-balances-api';
import { BalanceType } from '@/modules/balances/types/balances';
import { ManualBalances } from '@/modules/balances/types/manual-balances';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { awaitTaskOutcome } from './await-task';
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

describe('manual balances api contract', () => {
  it('should resolve the async balances query with the seeded balances', async () => {
    const pendingTask = await useManualBalancesApi().queryManualBalances();
    const { balances } = ManualBalances.parse(await awaitTaskOutcome(pendingTask));

    for (const seeded of contractExpected().manual_balances) {
      const match = balances.find(balance => balance.label === seeded.label);
      expect(match, `seeded manual balance '${seeded.label}' missing`).toBeDefined();
      expect(match?.asset).toBe(seeded.asset);
      expect(match?.amount.toString()).toBe(seeded.amount);
      expect(match?.location).toBe(seeded.location);
      // a positive value proves the valuation resolved from the seeded
      // manual latest prices without any oracle round-trip
      expect(match?.value.isPositive()).toBe(true);
    }
  });

  it('should add and delete a manual balance through the task flow', async () => {
    const manualBalancesApi = useManualBalancesApi();
    const label = 'contract test balance';
    const pendingTask = await manualBalancesApi.addManualBalances([{
      amount: bigNumberify(100),
      asset: 'EUR',
      balanceType: BalanceType.ASSET,
      label,
      location: 'banks',
      tags: null,
    }]);
    const { balances } = ManualBalances.parse(await awaitTaskOutcome(pendingTask));
    const added = balances.find(balance => balance.label === label);
    expect(added, 'added manual balance missing from task outcome').toBeDefined();
    expect(added?.amount.toString()).toBe('100');

    if (added === undefined)
      return;
    const remaining = await manualBalancesApi.deleteManualBalances([added.identifier]);
    expect(remaining.balances.find(balance => balance.label === label)).toBeUndefined();
  });
});
