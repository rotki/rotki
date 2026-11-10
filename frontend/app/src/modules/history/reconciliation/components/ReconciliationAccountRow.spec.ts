import type { useLocations } from '@/modules/core/common/use-locations';
import type { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import type { ReconciliationAccount, StatusCounts } from '@/modules/history/reconciliation/schemas';
import { Blockchain } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed } from 'vue';
import { createStatusError } from '@/modules/core/api/response-handlers';
import ReconciliationAccountRow from '@/modules/history/reconciliation/components/ReconciliationAccountRow.vue';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): ReturnType<typeof useSupportedChains> => createMock<ReturnType<typeof useSupportedChains>>({
    matchChain: (location: string) => (location === 'ethereum' ? Blockchain.ETH : undefined),
  }),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): ReturnType<typeof useLocations> => createMock<ReturnType<typeof useLocations>>({
    useLocationData: () => computed(() => undefined),
  }),
}));

function counts(overrides: Partial<StatusCounts> = {}): StatusCounts {
  return { blocked: 0, mismatch: 0, notCompared: 0, pending: 0, reconciled: 0, ...overrides };
}

function account(overrides: Partial<ReconciliationAccount> = {}): ReconciliationAccount {
  return {
    counts: counts(),
    historySyncedTo: null,
    isExchange: false,
    lastComparedAt: null,
    lastEventTs: null,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    ...overrides,
  };
}

function mountRow(props: { account: ReconciliationAccount; error?: unknown }): VueWrapper {
  return mount(ReconciliationAccountRow, {
    global: { stubs: { HashLink: { template: '<span data-testid="hash-link" />' } } },
    props: { colspan: 5, isOpen: false, view: 'all', ...props },
  });
}

describe('reconciliation account row', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show an exchange label in full instead of shortening it like an address', () => {
    const wrapper = mountRow({ account: account({ isExchange: true, location: 'kraken', locationLabel: 'kraken account' }) });

    expect(wrapper.find('[data-testid="hash-link"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="reconciliation-account-label"]').text()).toBe('kraken account');
  });

  it('should link a chain account label as an address', () => {
    const wrapper = mountRow({ account: account() });

    expect(wrapper.find('[data-testid="hash-link"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="reconciliation-account-label"]').exists()).toBe(false);
  });

  it.each([
    [{ mismatch: 1, blocked: 1 }, 'bg-rui-error'],
    [{ blocked: 1 }, 'bg-rui-warning'],
  ])('should colour the attention dot by the most urgent status for %o', (overrides, expected) => {
    const wrapper = mountRow({ account: account({ counts: counts(overrides) }) });

    expect(wrapper.get('[data-testid="reconciliation-account-attention"]').classes()).toContain(expected);
  });

  it('should name why the account failed to load instead of the raw summary', () => {
    const wrapper = mountRow({
      account: account(),
      error: createStatusError(500, 'database is locked', { cause: 'internal', message: 'database is locked', result: null }),
    });

    const strip = wrapper.get('[data-testid="reconciliation-account-failure"]');
    expect(strip.text()).toContain('data_issues.reconciliation.failure.account');
    expect(strip.text()).toContain('database is locked');
    expect(wrapper.find('[data-testid="reconciliation-account-summary"]').exists()).toBe(false);
  });
});
