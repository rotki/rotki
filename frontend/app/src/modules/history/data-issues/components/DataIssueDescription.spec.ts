import type { IssueDescription } from '@/modules/history/data-issues/types';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import DataIssueDescription from '@/modules/history/data-issues/components/DataIssueDescription.vue';

const { assetName, assetSymbol } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    assetName: ref<string>('Aave Ethereum Variable Debt USDT'),
    assetSymbol: ref<string>('variableDebtEthUSDT'),
  };
});

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { useAssetField: (_asset: () => string | undefined, field: string) => Ref<string> } => ({
    useAssetField: (_asset, field) => (field === 'symbol' ? assetSymbol : assetName),
  }),
}));

const I18nTSlotsStub = defineComponent({
  name: 'I18nT',
  props: {
    keypath: { required: true, type: String },
    tag: { default: 'span', type: String },
  },
  setup(props, { slots }): () => VNode {
    return (): VNode => h(
      props.tag,
      { 'data-keypath': props.keypath },
      Object.entries(slots).map(([name, slot]) => h('span', { 'data-slot': name }, slot?.())),
    );
  },
});

const ValueDisplayStub = defineComponent({
  name: 'ValueDisplay',
  props: {
    format: { default: undefined, type: Object },
    value: { required: true, type: Object },
  },
  setup(props): () => VNode {
    return (): VNode => {
      const decimals = props.format && 'decimals' in props.format && typeof props.format.decimals === 'number'
        ? String(props.format.decimals)
        : undefined;
      return h('span', {
        'data-decimals': decimals,
        'data-testid': 'value-display-stub',
      }, String(props.value));
    };
  },
});

function createWrapper(description: IssueDescription, short = false): VueWrapper {
  return mount(DataIssueDescription, {
    global: {
      stubs: {
        I18nT: I18nTSlotsStub,
        ValueDisplay: ValueDisplayStub,
      },
    },
    props: {
      description,
      short,
    },
  });
}

describe('dataIssueDescription', () => {
  it('should render the accruedInterest slot with exact decimals for standard token precision', () => {
    const wrapper = createWrapper({
      amounts: {
        accruedInterest: bigNumberify('0.00525'),
        delta: bigNumberify('50'),
        derived: bigNumberify('100'),
        observed: bigNumberify('150.00525'),
      },
      asset: 'eip155:1/erc20:0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8',
      messageKey: 'data_issues.description.current_balance_mismatch_with_interest',
      shortMessageKey: 'data_issues.description_short.current_balance_mismatch',
    });

    expect(wrapper.attributes('data-keypath')).toBe('data_issues.description.current_balance_mismatch_with_interest');
    const accruedInterest = wrapper.get('[data-slot="accruedInterest"] [data-testid="value-display-stub"]');
    expect(accruedInterest.text()).toBe('0.00525');
    expect(accruedInterest.attributes('data-decimals')).toBe('5');
  });

  it('should fall back to user precision for 78-decimal ray-derived accruedInterest and delta while keeping exact balance decimals', () => {
    const rayAccruedInterest = '46.4638039999999999999999900379158777898096267801723634815456113170195509546138';
    const rayDelta = '500.0000000000000000000000099620841222101903732198276365184543886829804490453862';
    const wrapper = createWrapper({
      amounts: {
        accruedInterest: bigNumberify(rayAccruedInterest),
        delta: bigNumberify(rayDelta),
        derived: bigNumberify('14004.209174'),
        observed: bigNumberify('14550.672978'),
      },
      asset: 'eip155:1/erc20:0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8',
      messageKey: 'data_issues.description.current_balance_mismatch_with_interest',
      shortMessageKey: 'data_issues.description_short.current_balance_mismatch',
    });

    expect(wrapper.get('[data-slot="accruedInterest"] [data-testid="value-display-stub"]').attributes('data-decimals')).toBeUndefined();
    expect(wrapper.get('[data-slot="delta"] [data-testid="value-display-stub"]').attributes('data-decimals')).toBeUndefined();
    expect(wrapper.get('[data-slot="derived"] [data-testid="value-display-stub"]').attributes('data-decimals')).toBe('6');
    expect(wrapper.get('[data-slot="observed"] [data-testid="value-display-stub"]').attributes('data-decimals')).toBe('6');
  });

  it('should omit the accruedInterest ValueDisplay when no accrued interest is present', () => {
    const wrapper = createWrapper({
      amounts: {
        delta: bigNumberify('5'),
        derived: bigNumberify('10'),
        observed: bigNumberify('15'),
      },
      asset: 'ETH',
      messageKey: 'data_issues.description.current_balance_mismatch',
      shortMessageKey: 'data_issues.description_short.current_balance_mismatch',
    });

    expect(wrapper.find('[data-slot="accruedInterest"] [data-testid="value-display-stub"]').exists()).toBe(false);
  });

  it('should switch to the short message key when short is true', () => {
    const wrapper = createWrapper({
      amounts: {
        accruedInterest: bigNumberify('5'),
        delta: bigNumberify('50'),
        derived: bigNumberify('100'),
        observed: bigNumberify('155'),
      },
      asset: 'ETH',
      messageKey: 'data_issues.description.current_balance_mismatch_with_interest',
      shortMessageKey: 'data_issues.description_short.current_balance_mismatch',
    }, true);

    expect(wrapper.attributes('data-keypath')).toBe('data_issues.description_short.current_balance_mismatch');
  });
});
