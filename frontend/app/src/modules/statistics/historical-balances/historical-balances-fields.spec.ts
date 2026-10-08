import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { createMock } from '@test/utils/create-mock';
import { get, set } from '@vueuse/shared';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { DisplayKinds } from '@/modules/core/table/pill/core/types';
import { historicalBalancesParams, toHistoricalBalancesFields } from './historical-balances-fields';

const resolvers = createMock<SharedFieldResolvers>({ resolveLocationName: (value: string): string => `name:${value}` });

function fields(): ReturnType<typeof toHistoricalBalancesFields> {
  return toHistoricalBalancesFields(resolvers, key => key, {
    accounts: {
      resolveCaption: () => undefined,
      resolveDisplay: value => (value.startsWith('0x') ? { kind: DisplayKinds.ADDRESS } : { kind: DisplayKinds.LOCATION, source: 'kraken' }),
      resolveKeywords: value => (value === '0xA' ? '0xA lefteris.eth' : value),
      resolveLabel: value => (value === '0xA' ? 'lefteris.eth' : value),
      suggest: () => ['0xA', 'Kraken 1'],
    },
    locations: () => ['ethereum', 'kraken'],
  });
}

function field(key: string): ReturnType<typeof fields>[number] {
  const found = fields().find(item => item.key === key);
  if (!found)
    throw new Error(`no ${key} field`);
  return found;
}

describe('toHistoricalBalancesFields', () => {
  it('should offer location, account and a keyword search, in one bar', () => {
    expect(fields().map(({ key }) => key)).toEqual(['location', 'account', 'search']);
  });

  it('should offer the day\'s locations, several at once, named and drawn as locations', () => {
    const location = field('location');

    expect(location.suggest?.()).toEqual(['ethereum', 'kraken']);
    expect(location.multiple).toBe(true);
    expect(location.display).toBe(DisplayKinds.LOCATION);
    expect(location.resolveLabel?.('ethereum')).toBe('name:ethereum');
  });

  it('should find an account by its name and draw an exchange account with the exchange\'s logo', () => {
    const account = field('account');

    expect(account.suggest?.()).toEqual(['0xA', 'Kraken 1']);
    expect(account.resolveKeywords?.('0xA')).toContain('lefteris.eth');
    expect(account.resolveDisplay?.('Kraken 1')).toEqual({ kind: DisplayKinds.LOCATION, source: 'kraken' });
  });

  it('should take the search as typed text', () => {
    expect(field('search').freeText).toBe(true);
  });
});

describe('historicalBalancesParams', () => {
  it('should write what the bar holds into the page\'s refs, and show only filters that are set', () => {
    const locations = ref<string[]>([]);
    const accounts = ref<string[]>([]);
    const search = ref<string>('');
    const params = historicalBalancesParams(locations, accounts, search);

    expect(get(params)).toEqual({});

    set(params, { accounts: ['0xA'], locations: ['ethereum', 'optimism'], search: 'usdc' });

    expect(get(locations)).toEqual(['ethereum', 'optimism']);
    expect(get(accounts)).toEqual(['0xA']);
    expect(get(search)).toBe('usdc');

    set(params, {});

    expect(get(locations)).toEqual([]);
    expect(get(search)).toBe('');
  });
});
