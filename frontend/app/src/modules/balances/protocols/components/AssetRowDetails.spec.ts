import type { StubInstance } from '@test/utils/component-vm';
import type { AssetBreakdownOptions } from '@/modules/balances/types/balances';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import '@test/i18n';

/**
 * `AssetRowDetails` sits between two components that both take the breakdown bag, so its job is to
 * unpack it correctly and hand the right pieces on. `ETH` picks the EvmNativeTokenBreakdown branch
 * (it is the only EVM native token) and any other identifier picks the nested AssetBalances branch.
 */
function stub(name: string, props: string[]): Record<string, unknown> {
  return defineComponent({ name, props, template: '<div />' });
}

function row(asset: string, withBreakdown = false): AssetBalanceWithPrice {
  return {
    amount: bigNumberify(1),
    asset,
    breakdown: withBreakdown ? [] : undefined,
    price: bigNumberify(2),
    value: bigNumberify(2),
  };
}

function createWrapper(
  breakdown?: AssetBreakdownOptions,
  asset = 'ETH',
): VueWrapper<InstanceType<typeof AssetRowDetails>> {
  return mount(AssetRowDetails, {
    global: {
      stubs: {
        AssetBalances: defineComponent({
          name: 'AssetBalances',
          props: {
            balances: { default: () => [], type: Array },
            breakdown: { default: undefined, type: Object },
            layout: { default: undefined, type: String },
            loading: { default: false, type: Boolean },
          },
          template: '<div />',
        }),
        AssetDetailsLayout: defineComponent({
          name: 'AssetDetailsLayout',
          props: ['row'],
          template: '<div><slot name="breakdown" /><slot name="perprotocol" /></div>',
        }),
        AssetProtocolBreakdown: stub('AssetProtocolBreakdown', ['data', 'asset', 'loading']),
        EvmNativeTokenBreakdown: stub('EvmNativeTokenBreakdown', [
          'assets',
          'blockchainOnly',
          'details',
          'identifier',
          'isLiability',
        ]),
      },
    },
    props: { breakdown, row: row(asset) },
  });
}

function native(wrapper: VueWrapper<InstanceType<typeof AssetRowDetails>>): VueWrapper<StubInstance> {
  return wrapper.findComponent<StubInstance>({ name: 'EvmNativeTokenBreakdown' });
}

function nested(wrapper: VueWrapper<InstanceType<typeof AssetRowDetails>>): VueWrapper<StubInstance> {
  return wrapper.findComponent<StubInstance>({ name: 'AssetBalances' });
}

describe('balances/protocols/components/AssetRowDetails.vue', () => {
  it('should default to the blockchain-only native breakdown when given no bag', () => {
    const wrapper = createWrapper();

    expect(native(wrapper).exists()).toBe(true);
    expect(native(wrapper).props('blockchainOnly')).toBe(true);
    expect(native(wrapper).props('isLiability')).toBe(false);
  });

  it('should widen the native breakdown past the chains when `all` is set', () => {
    expect(native(createWrapper({ all: true })).props('blockchainOnly')).toBe(false);
  });

  it('should mark the native breakdown as a liability when `isLiability` is set', () => {
    expect(native(createWrapper({ isLiability: true })).props('isLiability')).toBe(true);
  });

  it('should hand the scope on as the native breakdown details', () => {
    const scope = { chains: ['eth'], groupId: 'group-1' };

    expect(native(createWrapper({ scope })).props('details')).toStrictEqual(scope);
  });

  it('should fall back to the nested table when `hide` suppresses the native breakdown', () => {
    const wrapper = createWrapper({ hide: true });

    expect(native(wrapper).exists()).toBe(false);
    expect(nested(wrapper).exists()).toBe(true);
  });

  it('should forward the bag itself to the nested table so the recursion keeps its scope', () => {
    const breakdown: AssetBreakdownOptions = { hide: true, isLiability: true, scope: { groupId: 'g' } };

    expect(nested(createWrapper(breakdown)).props('breakdown')).toStrictEqual(breakdown);
  });

  it('should always hide the total on the nested table, whatever the outer hide asks for', () => {
    expect(nested(createWrapper(undefined, 'BTC')).props('layout')).toBe('nested');
  });

  /*
   * A forwarded optional value arrives as a present key holding `undefined`, which a
   * `{ ...DEFAULTS, ...bag }` spread would keep over the default. Only `isLiability` exposes that,
   * since it is passed on as a prop where `undefined !== false`; `all` and `hide` are only read as
   * booleans.
   */
  it('should keep the isLiability default when the bag holds an explicit undefined', () => {
    expect(native(createWrapper({ isLiability: undefined })).props('isLiability')).toBe(false);
  });
});
