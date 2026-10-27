import type { DivergenceBoundaryEvent } from '@/modules/history/balances/use-balance-divergence';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { type ComputedRef, defineComponent } from 'vue';
import DivergenceComparison from '@/modules/history/balances/DivergenceComparison.vue';

const stubs = {
  AmountDiffDisplay: {
    props: ['amount', 'reference', 'decimals'],
    template: '<span class="amount diff" :data-decimals="decimals" :data-reference="reference?.toString()">{{ amount?.toString() }}</span>',
  },
  AssetAmountDisplay: {
    props: ['amount', 'asset', 'decimals'],
    template: '<span class="amount" :data-decimals="decimals">{{ amount?.toString() }}</span>',
  },
  DateDisplay: { props: { milliseconds: Boolean, timestamp: Number }, template: '<span class="date" :data-milliseconds="String(milliseconds)">{{ timestamp }}</span>' },
  DivergenceSearchWindow: {
    props: ['from', 'to'],
    template: '<div data-testid="divergence-gap">{{ from.eventIdentifier }}-{{ to.eventIdentifier }}</div>',
  },
  HashLink: { props: ['text'], template: '<span class="hash">{{ text }}</span>' },
  RuiButton: defineComponent({
    emits: ['click'],
    props: { disabled: Boolean },
    template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot name="prepend" /><slot /></button>',
  }),
  RuiIcon: { props: ['name'], template: '<i class="icon" :data-name="name" />' },
};

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { useAssetField: (identifier: () => string | undefined) => ComputedRef<string> } => ({
    useAssetField: identifier => computed<string>(() => toValue(identifier) ?? ''),
  }),
}));

function lastMatching(overrides: Partial<DivergenceBoundaryEvent['event']> = {}): DivergenceBoundaryEvent {
  return {
    color: 'success',
    event: {
      blockNumber: 11,
      difference: bigNumberify('0'),
      eventIdentifier: 101,
      groupIdentifier: `1${'a'.repeat(64)}`,
      onchainBalance: bigNumberify('5'),
      timestamp: 100,
      trackedBalance: bigNumberify('5'),
      txHash: `0x${'a'.repeat(64)}`,
      ...overrides,
    },
    key: 'last_matching',
  };
}

function firstDiverged(overrides: Partial<DivergenceBoundaryEvent['event']> = {}): DivergenceBoundaryEvent {
  return {
    color: 'warning',
    event: {
      blockNumber: 22,
      difference: bigNumberify('-0.086834'),
      eventIdentifier: 202,
      groupIdentifier: `1${'b'.repeat(64)}`,
      onchainBalance: bigNumberify('5.296366'),
      timestamp: 200,
      trackedBalance: bigNumberify('5.3832'),
      txHash: `0x${'b'.repeat(64)}`,
      ...overrides,
    },
    key: 'first_diverged',
  };
}

function createWrapper(boundaries: DivergenceBoundaryEvent[], footer?: string): VueWrapper {
  return mount(DivergenceComparison, {
    global: { stubs },
    props: { asset: 'USDC', boundaries },
    slots: footer ? { footer } : {},
  });
}

describe('divergenceComparison', () => {
  it('should render one column per boundary, linking the transaction hash rather than the group identifier', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()]);

    expect(wrapper.find('[data-testid=divergence-boundary][data-key=last_matching]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=divergence-boundary][data-key=first_diverged]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid=divergence-tx] .hash').map(hash => hash.text())).toEqual([`0x${'a'.repeat(64)}`, `0x${'b'.repeat(64)}`]);
  });

  it('should leave the block numbers to the search window when there is one', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()]);

    expect(wrapper.find('[data-testid=divergence-block]').exists()).toBe(false);
  });

  it('should show the block under the date when a single boundary leaves no search window', () => {
    const wrapper = createWrapper([firstDiverged()]);

    expect(wrapper.get('[data-testid=divergence-block][data-key=first_diverged]').text()).toContain('22');
  });

  it('should compare each tracked balance against the on-chain one, and each on-chain one against the tracked', () => {
    const wrapper = createWrapper([firstDiverged()]);

    const [tracked, onchain] = wrapper.findAll('.diff');
    expect(tracked.text()).toBe('5.3832');
    expect(tracked.attributes('data-reference')).toBe('5.296366');
    expect(onchain.text()).toBe('5.296366');
    expect(onchain.attributes('data-reference')).toBe('5.3832');
  });

  it('should render the footer slot below the table', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()], 'Checked 10 points.');

    expect(wrapper.get('[data-testid=divergence-footer]').text()).toMatch(/^Checked 10 points\./);
  });

  it('should show each boundary event date from a timestamp in seconds', () => {
    const wrapper = createWrapper([lastMatching({ timestamp: 1790000000 }), firstDiverged({ timestamp: 1790000600 })]);

    const first = wrapper.get('[data-testid=divergence-date][data-key=last_matching]');
    const second = wrapper.get('[data-testid=divergence-date][data-key=first_diverged]');
    expect(first.text()).toBe('1790000000');
    expect(first.attributes('data-milliseconds')).toBe('false');
    expect(second.text()).toBe('1790000600');
  });

  it('should give the search window the last matching and first diverged events', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()]);

    expect(wrapper.get('[data-testid=divergence-gap]').text()).toBe('101-202');
  });

  it('should not show a search window when only one boundary event exists', () => {
    const wrapper = createWrapper([firstDiverged()]);

    expect(wrapper.find('[data-testid=divergence-gap]').exists()).toBe(false);
  });

  it('should say the tracked balance is higher when the difference is negative, without repeating the amount', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()]);

    const headline = wrapper.get('[data-testid=divergence-headline]');
    expect(headline.text()).toContain('balance_divergence.tracked_higher');
    expect(headline.find('.amount').exists()).toBe(false);
  });

  it('should say the tracked balance is lower when the difference is positive', () => {
    const wrapper = createWrapper([firstDiverged({ difference: bigNumberify('0.5') })]);

    expect(wrapper.get('[data-testid=divergence-headline]').text()).toContain('balance_divergence.tracked_lower');
  });

  it('should not render a headline when nothing diverged', () => {
    const wrapper = createWrapper([lastMatching()]);

    expect(wrapper.find('[data-testid=divergence-headline]').exists()).toBe(false);
  });

  it('should render every non-zero amount at the largest precision in the table so nothing is rounded away', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()]);

    const amounts = wrapper.findAll('.amount');
    expect(amounts).toHaveLength(5);
    expect(new Set(amounts.map(amount => amount.attributes('data-decimals')))).toEqual(new Set(['6']));
  });

  it('should mark an exact zero difference as a match instead of a value', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()]);

    expect(wrapper.get('[data-testid=divergence-match][data-key=last_matching]').text()).toContain('balance_divergence.match');
    expect(wrapper.find('[data-testid=divergence-difference][data-key=last_matching]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=divergence-match][data-key=first_diverged]').exists()).toBe(false);
  });

  it('should still show a non-zero difference that falls within tolerance on the matching side', () => {
    const wrapper = createWrapper([lastMatching({ difference: bigNumberify('0.000001') }), firstDiverged()]);

    expect(wrapper.get('[data-testid=divergence-difference][data-key=last_matching]').text()).toBe('0.000001');
    expect(wrapper.find('[data-testid=divergence-match]').exists()).toBe(false);
  });

  it('should state the asset unit once, in the corner of the table', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()]);

    expect(wrapper.get('[data-testid=divergence-unit]').text()).toBe('USDC');
  });

  it('should mark each footer transaction with the icon of its column', () => {
    const wrapper = createWrapper([lastMatching(), firstDiverged()]);

    expect(wrapper.get('[data-testid=divergence-tx][data-key=last_matching] .icon').attributes('data-name')).toBe('lu-check');
    expect(wrapper.get('[data-testid=divergence-tx][data-key=first_diverged] .icon').attributes('data-name')).toBe('lu-triangle-alert');
  });

  it('should emit view with the boundary whose button was clicked', async () => {
    const diverged = firstDiverged();
    const wrapper = createWrapper([lastMatching(), diverged]);

    await wrapper.get('[data-testid=view-divergence][data-key=first_diverged]').trigger('click');

    expect(wrapper.emitted('view')).toEqual([[diverged]]);
  });

  it('should show the missing transaction label when a boundary has no transaction hash', () => {
    const wrapper = createWrapper([lastMatching({ txHash: null })]);

    expect(wrapper.find('.hash').exists()).toBe(false);
    expect(wrapper.text()).toContain('balance_divergence.missing_group');
  });

  it('should disable the view button when a boundary has no group identifier', () => {
    const wrapper = createWrapper([lastMatching({ groupIdentifier: null })]);

    expect(wrapper.get('[data-testid=view-divergence][data-key=last_matching]').attributes('disabled')).toBeDefined();
  });
});
