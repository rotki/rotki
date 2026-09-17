import { bigNumberify, Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import SourceLegend from '@/modules/dashboard/holdings/components/SourceLegend.vue';
import { type HoldingsSummary, type SourceContribution, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { summarizeSources } from '@/modules/dashboard/holdings/core/source-summary';
import '@test/i18n';

const contributions: SourceContribution[] = [
  { chain: 'eth', kind: SourceKind.BLOCKCHAIN, loading: false, value: bigNumberify(300) },
  { kind: SourceKind.EXCHANGE, loading: false, location: 'kraken', value: bigNumberify(100) },
];

const stubs = {
  AddSourceMenu: { template: '<div data-testid="add-source-menu" />' },
  FiatDisplay: { props: ['value'], template: '<span data-testid="fiat">{{ value.toFixed() }}</span>' },
  PercentageDisplay: { props: ['value'], template: '<span data-testid="percentage">{{ value }}</span>' },
  RuiIcon: true,
  RuiSkeletonLoader: { template: '<div data-testid="legend-skeleton" />' },
};

function createWrapper(summary: HoldingsSummary, props: { selectedKind?: SourceKind; loading?: boolean } = {}): VueWrapper<InstanceType<typeof SourceLegend>> {
  return mount(SourceLegend, { global: { stubs }, props: { summary, ...props } });
}

function rows(wrapper: VueWrapper): string[] {
  return wrapper.findAll('[data-testid=dashboard-source-legend-row]').map(row => row.attributes('data-kind') ?? '');
}

describe('sourceLegend', () => {
  it('should list each source kind with its value and share', () => {
    const wrapper = createWrapper(summarizeSources(contributions, { liabilities: Zero, nfts: bigNumberify(100) }));

    expect(rows(wrapper)).toEqual(['blockchain', 'exchange', 'nft']);
    expect(wrapper.findAll('[data-testid=percentage]').map(share => share.text())).toEqual(['60.00', '20.00', '20.00']);
  });

  it('should ask to narrow the tiles to a kind, and to clear it when that kind is picked again', async () => {
    const summary = summarizeSources(contributions, { liabilities: Zero, nfts: undefined });

    const idle = createWrapper(summary);
    await idle.find('[data-kind=exchange]').trigger('click');
    expect(idle.emitted('select')).toEqual([['exchange']]);

    const selected = createWrapper(summary, { selectedKind: SourceKind.EXCHANGE });
    expect(selected.find('[data-kind=exchange]').attributes('aria-pressed')).toBe('true');
    await selected.find('[data-kind=exchange]').trigger('click');
    expect(selected.emitted('select')).toEqual([[undefined]]);
  });

  it('should jump to the NFT table instead of narrowing when the NFT row is picked', async () => {
    const wrapper = createWrapper(summarizeSources(contributions, { liabilities: Zero, nfts: bigNumberify(100) }));
    await wrapper.find('[data-kind=nft]').trigger('click');

    expect(wrapper.emitted('jump')).toEqual([['nft']]);
    expect(wrapper.emitted('select')).toBeUndefined();
  });

  it('should show liabilities as a negative line only when there are any', async () => {
    const without = createWrapper(summarizeSources(contributions, { liabilities: Zero, nfts: undefined }));
    expect(without.find('[data-testid=dashboard-source-legend-liabilities]').exists()).toBe(false);

    const withLiabilities = createWrapper(summarizeSources(contributions, { liabilities: bigNumberify(50), nfts: undefined }));
    const line = withLiabilities.find('[data-testid=dashboard-source-legend-liabilities]');
    expect(line.find('[data-testid=fiat]').text()).toBe('-50');
    await line.trigger('click');
    expect(withLiabilities.emitted('jump')).toEqual([['liabilities']]);
  });

  it('should offer to add a source only while some kind is empty', () => {
    expect(createWrapper(summarizeSources(contributions, { liabilities: Zero, nfts: undefined })).find('[data-testid=add-source-menu]').exists()).toBe(true);

    const everyKind: SourceContribution[] = [
      ...contributions,
      { kind: SourceKind.BANK, loading: false, location: 'qonto', value: bigNumberify(1) },
      { kind: SourceKind.MANUAL, loading: false, location: 'external', value: bigNumberify(1) },
    ];
    expect(createWrapper(summarizeSources(everyKind, { liabilities: Zero, nfts: undefined })).find('[data-testid=add-source-menu]').exists()).toBe(false);
  });

  it('should show a kind still being priced with a placeholder instead of its partial value and share', () => {
    const wrapper = createWrapper(summarizeSources([
      { chain: 'btc', kind: SourceKind.BLOCKCHAIN, loading: true, value: Zero },
      { kind: SourceKind.EXCHANGE, loading: false, location: 'kraken', value: bigNumberify(100) },
    ], { liabilities: Zero, nfts: undefined }));

    expect(rows(wrapper)).toEqual(['blockchain', 'exchange']);
    const blockchain = wrapper.find('[data-kind=blockchain]');
    expect(blockchain.find('[data-testid=legend-skeleton]').exists()).toBe(true);
    expect(blockchain.find('[data-testid=fiat]').exists()).toBe(false);
    expect(blockchain.find('[data-testid=percentage]').exists()).toBe(false);
    expect(wrapper.find('[data-kind=exchange] [data-testid=fiat]').text()).toBe('100');
  });

  it('should show skeleton rows and no add action while the first load runs', () => {
    const wrapper = createWrapper(summarizeSources([], { liabilities: Zero, nfts: undefined }), { loading: true });

    expect(wrapper.findAll('[data-testid=legend-skeleton]')).toHaveLength(4);
    expect(wrapper.find('[data-testid=add-source-menu]').exists()).toBe(false);
  });
});
