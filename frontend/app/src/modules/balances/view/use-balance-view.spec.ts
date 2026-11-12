import type { LocationQuery } from 'vue-router';
import { bigNumberify } from '@rotki/common';
import { get } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, nextTick } from 'vue';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { BalanceView } from '@/modules/balances/view/balance-view';
import { useBalanceView } from '@/modules/balances/view/use-balance-view';

const h = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    ensureLoaded: vi.fn<() => Promise<void>>(),
    flag: { enabled: true },
    premium: ref<boolean>(true),
    query: ref<LocationQuery>({}),
    replace: vi.fn<(location: { query: LocationQuery }) => Promise<void>>(),
  };
});

vi.mock('vue-router', async () => {
  const { computed } = await import('vue');
  return {
    useRoute: (): object => computed(() => ({ query: h.query.value })),
    useRouter: (): object => ({ replace: h.replace }),
  };
});
vi.mock('@/modules/premium/use-premium', () => ({ usePremium: (): object => h.premium }));
vi.mock('@/modules/core/common/feature-flags', () => ({ isAccountingUpdateEnabled: (): boolean => h.flag.enabled }));
vi.mock('@/modules/balances/use-current-historical-balances', () => ({
  useCurrentHistoricalBalances: (): object => ({ ensureLoaded: h.ensureLoaded }),
}));

let scope: EffectScope;

function create(): ReturnType<typeof useBalanceView> {
  const state = scope.run(() => useBalanceView());
  if (!state)
    throw new Error('composable returned undefined outside an effect scope');
  return state;
}

describe('useBalanceView', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useHistoricalSnapshotStore().setSnapshot({
      entries: [{ amount: bigNumberify(1), asset: 'ETH', location: 'ethereum', locationLabel: '0xA', protocol: null }],
      processingRequired: false,
      stale: false,
    });
    scope = effectScope();
    h.flag.enabled = true;
    h.premium.value = true;
    h.query.value = {};
    h.replace.mockReset().mockResolvedValue(undefined);
    h.ensureLoaded.mockReset().mockResolvedValue(undefined);
  });

  afterEach(() => scope.stop());

  it('should read the history view from the route query', () => {
    h.query.value = { view: 'history' };

    expect(get(create().isHistory)).toBe(true);
  });

  it('should read queried when the query names no view', () => {
    expect(get(create().view)).toBe(BalanceView.QUERIED);
  });

  it('should read queried for a history query without premium, and offer no switch', () => {
    h.premium.value = false;
    h.query.value = { view: 'history' };
    const { available, isHistory } = create();

    expect(get(available)).toBe(false);
    expect(get(isHistory)).toBe(false);
  });

  it('should read queried for a history query when the accounting update is off', () => {
    h.flag.enabled = false;
    h.query.value = { view: 'history' };

    expect(get(create().isHistory)).toBe(false);
  });

  it('should read queried for a history query before history has been processed', () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: [], processingRequired: true, stale: false });
    h.query.value = { view: 'history' };
    const { historyReady, isHistory } = create();

    expect(get(historyReady)).toBe(false);
    expect(get(isHistory)).toBe(false);
  });

  it('should write the history view into the query and keep the other query keys', async () => {
    h.query.value = { tab: 'assets' };
    await create().setView(BalanceView.HISTORY);

    expect(h.replace).toHaveBeenCalledExactlyOnceWith({ query: { tab: 'assets', view: 'history' } });
  });

  it('should drop the view key when switching back to queried', async () => {
    h.query.value = { tab: 'assets', view: 'history' };
    await create().setView(BalanceView.QUERIED);

    expect(h.replace).toHaveBeenCalledExactlyOnceWith({ query: { tab: 'assets' } });
  });

  it('should load the history snapshot once the view is available', async () => {
    h.premium.value = false;
    create();
    expect(h.ensureLoaded).not.toHaveBeenCalled();

    h.premium.value = true;
    await nextTick();
    expect(h.ensureLoaded).toHaveBeenCalledOnce();
  });
});
