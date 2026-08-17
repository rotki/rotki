import type { AssetBreakdownOptions } from '@/modules/balances/types/balances';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { type ComponentPublicInstance, defineComponent } from 'vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import '@test/i18n';

type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

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
        // `hideTotal` needs its Boolean type declared or the valueless `hide-total` attribute
        // arrives as the empty string instead of `true`.
        AssetBalances: defineComponent({
          name: 'AssetBalances',
          props: {
            balances: { default: () => [], type: Array },
            breakdown: { default: undefined, type: Object },
            hideTotal: { default: false, type: Boolean },
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

  // A non-native asset takes the nested branch regardless of `hide`, and the nested table always
  // suppresses its own total row: that is the whole reason the prop is hardcoded rather than passed.
  it('should always hide the total on the nested table', () => {
    expect(nested(createWrapper(undefined, 'BTC')).props('hideTotal')).toBe(true);
  });

  /*
   * The discriminating case for the bag. A caller that forwards its own optional value produces a
   * present key holding `undefined`, and `{ ...DEFAULTS, ...bag }` would take that as the value
   * instead of the default. Every "default applies" and "explicit value wins" test above passes
   * either way, so without this one the suite is compatible with that bug.
   *
   * `isLiability` is the only field where it is observable, and a negative control proved it: with a
   * spread in place of the `??` reads, this test fails and the equivalent ones for `all` and `hide`
   * both still pass. Those two are only ever consumed in a boolean context (`!all` and a `v-if`),
   * where `undefined` and `false` are indistinguishable, so there is nothing there to catch. This
   * one is observable because the value is handed on as a prop, where `undefined !== false`.
   */
  it('should keep the isLiability default when the bag holds an explicit undefined', () => {
    expect(native(createWrapper({ isLiability: undefined })).props('isLiability')).toBe(false);
  });
});
