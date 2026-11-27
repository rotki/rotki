import type { LocationQuery } from 'vue-router';
import { get, set } from '@vueuse/shared';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, reactive } from 'vue';
import { AccountHistoryRange } from './account-history-selection';
import { useAccountHistorySelection } from './use-account-history-selection';

/** The route the composable reads, reactive like the real one so its computed selection follows it. */
const route = reactive<{ query: LocationQuery }>({ query: {} });

const router = vi.hoisted(() => ({ replace: vi.fn<(location: { query: LocationQuery }) => Promise<void>>() }));

vi.mock('vue-router', () => ({
  useRoute: (): { query: LocationQuery } => route,
  useRouter: (): { replace: typeof router.replace } => ({ replace: router.replace }),
}));

let scope: ReturnType<typeof effectScope>;

function create(): ReturnType<typeof useAccountHistorySelection> {
  const state = scope.run(() => useAccountHistorySelection());
  assert(state);
  return state;
}

describe('useAccountHistorySelection', () => {
  beforeEach(() => {
    scope = effectScope();
    route.query = {};
    router.replace.mockReset().mockImplementation(async ({ query }) => {
      route.query = query;
    });
  });

  afterEach(() => scope.stop());

  it('should read the selection from the route query', () => {
    route.query = { account: '0xA', asset: 'ETH', range: '1y' };
    const { selection } = create();

    expect(get(selection)).toEqual({ account: '0xA', asset: 'ETH', location: undefined, range: AccountHistoryRange.YEAR });
  });

  it('should clear the asset and location when another account is picked', () => {
    route.query = { account: '0xA', asset: 'ETH', location: 'optimism', range: '3m' };
    const { modelAccount } = create();

    set(modelAccount, '0xB');

    expect(router.replace).toHaveBeenCalledExactlyOnceWith({ query: { account: '0xB', range: '3m' } });
  });

  it('should clear the location when another asset is picked', () => {
    route.query = { account: '0xA', asset: 'ETH', location: 'optimism' };
    const { modelAsset } = create();

    set(modelAsset, 'DAI');

    expect(router.replace).toHaveBeenCalledExactlyOnceWith({ query: { account: '0xA', asset: 'DAI' } });
  });

  it('should keep the account and asset when the location or range changes', () => {
    route.query = { account: '0xA', asset: 'ETH' };
    const { modelLocation, modelRange, selection } = create();

    set(modelLocation, 'ethereum');
    set(modelRange, AccountHistoryRange.MONTH);

    expect(get(selection)).toEqual({ account: '0xA', asset: 'ETH', location: 'ethereum', range: AccountHistoryRange.MONTH });
  });

  it('should change nothing when a picker writes back the value it already holds', () => {
    route.query = { account: '0xA', asset: 'ETH', location: 'optimism', range: '3m' };
    const { modelAccount, modelAsset, modelLocation, modelRange } = create();

    set(modelAccount, '0xA');
    set(modelAsset, 'ETH');
    set(modelLocation, 'optimism');
    set(modelRange, AccountHistoryRange.QUARTER);

    expect(router.replace).not.toHaveBeenCalled();
  });

  it('should leave query keys it does not own untouched', () => {
    route.query = { account: '0xA', page: '2' };
    const { modelRange } = create();

    set(modelRange, AccountHistoryRange.MONTH);

    expect(router.replace).toHaveBeenCalledExactlyOnceWith({ query: { account: '0xA', page: '2', range: '1m' } });
  });
});
