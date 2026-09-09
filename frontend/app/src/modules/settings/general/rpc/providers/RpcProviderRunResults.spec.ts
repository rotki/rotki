import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import RpcProviderRunResults from '@/modules/settings/general/rpc/providers/RpcProviderRunResults.vue';
import { RPC_SETUP_STATUS, type RpcSetupRow, type RpcSetupSummary } from '@/modules/settings/general/rpc/providers/use-rpc-provider-setup';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    getChainName: (chain: string): string => chain,
  }),
}));

function row(overrides: Partial<RpcSetupRow> = {}): RpcSetupRow {
  return {
    chain: Blockchain.OPTIMISM,
    endpoint: 'https://optimism-mainnet.infura.io/v3/abcdef',
    name: 'Infura',
    status: RPC_SETUP_STATUS.ADDED,
    ...overrides,
  };
}

function summaryOf(rows: RpcSetupRow[]): RpcSetupSummary {
  return {
    added: rows.filter(item => item.status === RPC_SETUP_STATUS.ADDED).length,
    archive: rows.filter(item => item.archive).length,
    failed: rows.filter(item => item.status === RPC_SETUP_STATUS.FAILED).length,
    total: rows.length,
  };
}

function mountResults(rows: RpcSetupRow[], running = false, credential = ''): VueWrapper {
  return mount(RpcProviderRunResults, {
    global: { stubs: { ChainIcon: true } },
    props: { credential, rows, running, summary: summaryOf(rows) },
  });
}

describe('settings/general/rpc/providers/RpcProviderRunResults.vue', () => {
  it('should count what failed next to what was added', () => {
    const wrapper = mountResults([
      row({ chain: Blockchain.ETH }),
      row({ error: 'nope', status: RPC_SETUP_STATUS.FAILED }),
    ]);

    expect(wrapper.find('[data-testid=provider-added-count]').text()).toContain('apply.count.added');
    expect(wrapper.find('[data-testid=provider-failed-count]').text()).toContain('apply.count.failed');
  });

  it('should tell the user to expand while a failure is collapsed', async () => {
    const wrapper = mountResults([row({ error: 'nope', status: RPC_SETUP_STATUS.FAILED })]);

    expect(wrapper.find('[data-testid=provider-details-hint]').text()).toContain('apply.expand_failed');

    await wrapper.find('[data-testid=provider-details] [data-accordion-trigger]').trigger('click');
    await nextTick();

    expect(wrapper.find('[data-testid=provider-details-hint]').exists()).toBe(false);
  });

  it('should leave the expand hint off a run that added every chain', () => {
    const wrapper = mountResults([row()]);

    expect(wrapper.find('[data-testid=provider-details-hint]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=provider-failed-count]').exists()).toBe(false);
  });

  it('should name the chain it is connecting to while the run works', () => {
    const wrapper = mountResults([
      row({ chain: Blockchain.ETH }),
      row({ status: RPC_SETUP_STATUS.RUNNING }),
    ], true);

    const progress = wrapper.find('[data-testid=provider-progress]');
    expect(progress.text()).toContain('apply.progress_chain');
    expect(progress.find('chain-icon-stub').attributes('chain')).toBe(Blockchain.OPTIMISM);
    expect(wrapper.find('[data-testid=provider-progress-count]').text()).toContain('apply.progress_count');
  });

  it('should fall back to the counts in the gap between two chains', () => {
    const wrapper = mountResults([row({ status: RPC_SETUP_STATUS.PENDING })], true);

    const progress = wrapper.find('[data-testid=provider-progress]');
    expect(progress.text()).toContain('apply.progress');
    expect(progress.text()).not.toContain('apply.progress_chain');
    expect(progress.find('chain-icon-stub').exists()).toBe(false);
  });

  it('should keep the key out of a message that quotes the endpoint', () => {
    const error = 'Failed to connect at https://optimism-mainnet.infura.io/v3/abcdef and https://optimism-mainnet.infura.io/v3/abcdef';
    const wrapper = mountResults([row({ error, status: RPC_SETUP_STATUS.FAILED })], false, 'abcdef');

    const message = wrapper.find('[data-testid=provider-result]').text();
    expect(message).toContain('Failed to connect at');
    expect(message).not.toContain('abcdef');
  });

  it('should announce the run, which is the only place its state is told', () => {
    const wrapper = mountResults([row()]);

    expect(wrapper.find('[data-testid=provider-summary]').attributes('aria-live')).toBe('polite');
  });
});
