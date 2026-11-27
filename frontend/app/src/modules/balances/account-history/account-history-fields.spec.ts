import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { DataIssueAccountOptions } from '@/modules/history/data-issues/use-data-issue-account-options';
import { createMock } from '@test/utils/create-mock';
import { get, set } from '@vueuse/shared';
import { describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { accountHistoryParams, toAccountHistoryFields } from './account-history-fields';

const resolvers = createMock<SharedFieldResolvers>({});
const accounts = createMock<DataIssueAccountOptions>({ suggest: (): string[] => ['0xA', 'Kraken main'] });
const searchAsset = vi.fn();

describe('toAccountHistoryFields', () => {
  it('should offer one account and one asset, each a single value', () => {
    const fields = toAccountHistoryFields(resolvers, key => key, { accounts, assets: (): string[] => ['ETH'], searchAsset });

    expect(fields.map(({ key }) => key)).toEqual(['account', 'asset']);
    expect(fields.every(field => !field.multiple)).toBe(true);
    expect(fields[0]?.suggest?.()).toEqual(['0xA', 'Kraken main']);
  });

  it('should offer only the held assets when they are known, and search every asset otherwise', () => {
    const held = toAccountHistoryFields(resolvers, key => key, { accounts, assets: (): string[] => ['ETH'], searchAsset })[1];
    const any = toAccountHistoryFields(resolvers, key => key, { accounts, assets: undefined, searchAsset })[1];

    expect(held?.suggest?.()).toEqual(['ETH']);
    expect(held?.searchAsset).toBeUndefined();
    expect(held?.valueType).not.toBe('asset');
    expect(any?.valueType).toBe('asset');
    expect(any?.searchAsset).toBe(searchAsset);
    expect(any?.suggest).toBeUndefined();
  });
});

describe('accountHistoryParams', () => {
  it('should write the bar into the selection and show a pill only for what is picked', () => {
    const account = ref<string>();
    const asset = ref<string>();
    const params = accountHistoryParams(account, asset);
    expect(get(params)).toEqual({});

    set(params, { account: '0xA', asset: 'ETH' });

    expect(get(account)).toBe('0xA');
    expect(get(asset)).toBe('ETH');
    expect(get(params)).toEqual({ account: '0xA', asset: 'ETH' });
  });
});
