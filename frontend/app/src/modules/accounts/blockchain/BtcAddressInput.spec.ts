import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { XpubKeyType, type XpubPayload } from '@/modules/accounts/blockchain-accounts';
import BtcAddressInput from '@/modules/accounts/blockchain/BtcAddressInput.vue';
import { XpubPrefix } from '@/modules/accounts/xpub';

const ZPUB_KEY = 'zpub6rFR7y4Q2AijBEqTUqyzEyyxJewTSzAoot2vTBgN9r2fUKFJFfQwMiJZ2mq5YEZb6jhLjPtqyRUFHCBs7WkBCCesb5KMRE9T4cFT2UPyBYF';
const YPUB_KEY = 'ypub6Ww3ibxVfGzLrAH1PNcjyAWPKPPjLzQ7T9Mmfa18oF5dKaPSLDB6FghfZ1XxjVCGX2j4YMEsBX4M7Krjq6iHHJE97J7MkLgv6QC8MWKDXBL';
const XPUB_KEY = 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtyPWKiMJ7abWaX2ZFGvV3Gg7FbqXdRxivu1nQFCWEPa4UUgJGPkExPNm5';
const BTC_ADDRESS = 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq';

function createWrapper(blockchain: Blockchain.BTC | Blockchain.BCH = Blockchain.BTC): VueWrapper {
  return mount(BtcAddressInput, {
    global: {
      stubs: {
        RuiButton: {
          inheritAttrs: true,
          props: ['variant', 'color', 'size', 'disabled', 'icon'],
          template: '<button :data-variant="variant" @click="$emit(\'click\')"><slot /></button>',
        },
        RuiChip: true,
        RuiIcon: true,
        RuiMenuSelect: {
          emits: ['update:modelValue'],
          props: ['modelValue', 'options'],
          template: '<div />',
        },
        RuiTextField: {
          emits: ['update:modelValue', 'paste', 'blur'],
          props: ['modelValue', 'disabled'],
          template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
        RuiTooltip: true,
      },
    },
    props: {
      blockchain,
      disabled: false,
      errorMessages: {},
      xpub: undefined,
    },
  });
}

async function lastEmittedXpub(wrapper: VueWrapper): Promise<XpubPayload | undefined> {
  await nextTick();
  const events = wrapper.emitted<[XpubPayload | undefined]>('update:xpub');
  return events?.at(-1)?.[0];
}

describe('modules/accounts/blockchain/BtcAddressInput', () => {
  let wrapper: VueWrapper;

  afterEach(() => {
    wrapper?.unmount();
  });

  async function setXpubValue(value: string): Promise<void> {
    const input = wrapper.find('input');
    await input.setValue(value);
    await nextTick();
  }

  it('should auto-select Native SegWit when a zpub is entered without showing the disambiguation prompt', async () => {
    wrapper = createWrapper(Blockchain.BTC);
    await setXpubValue(ZPUB_KEY);

    expect(wrapper.find('[data-cy="xpub-disambiguation"]').exists()).toBe(false);
    const payload = await lastEmittedXpub(wrapper);
    expect(payload?.xpubType).toBe(XpubKeyType.ZPUB);
    expect(payload?.xpub).toBe(ZPUB_KEY);
  });

  it('should auto-select SegWit when a ypub is entered without showing the disambiguation prompt', async () => {
    wrapper = createWrapper(Blockchain.BTC);
    await setXpubValue(YPUB_KEY);

    expect(wrapper.find('[data-cy="xpub-disambiguation"]').exists()).toBe(false);
    const payload = await lastEmittedXpub(wrapper);
    expect(payload?.xpubType).toBe(XpubKeyType.YPUB);
  });

  it('should show all four address-type choices and default to Native SegWit when an xpub is entered on BTC', async () => {
    wrapper = createWrapper(Blockchain.BTC);
    await setXpubValue(XPUB_KEY);

    expect(wrapper.find('[data-cy="xpub-disambiguation"]').exists()).toBe(true);
    for (const prefix of [XpubPrefix.ZPUB, XpubPrefix.YPUB, XpubPrefix.P2TR, XpubPrefix.XPUB])
      expect(wrapper.find(`[data-cy="xpub-disambiguation-${prefix}"]`).exists()).toBe(true);

    const payload = await lastEmittedXpub(wrapper);
    expect(payload?.xpubType).toBe(XpubKeyType.ZPUB);
  });

  it('should update the payload when the user picks a different address type from the disambiguation buttons', async () => {
    wrapper = createWrapper(Blockchain.BTC);
    await setXpubValue(XPUB_KEY);

    const buttons = wrapper.findAll('[data-cy^="xpub-disambiguation-"]');
    expect(buttons).toHaveLength(4);
    const p2trButton = buttons.find(b => b.attributes('data-cy') === `xpub-disambiguation-${XpubPrefix.P2TR}`);
    expect(p2trButton).toBeDefined();
    await p2trButton!.trigger('click');
    await nextTick();

    const payload = await lastEmittedXpub(wrapper);
    expect(payload?.xpubType).toBe(XpubKeyType.P2TR);
    expect(wrapper.find('[data-cy="xpub-disambiguation"]').exists()).toBe(true);
  });

  it('should silently pick Legacy on BCH without showing the disambiguation prompt', async () => {
    wrapper = createWrapper(Blockchain.BCH);
    await setXpubValue(XPUB_KEY);

    expect(wrapper.find('[data-cy="xpub-disambiguation"]').exists()).toBe(false);
    const payload = await lastEmittedXpub(wrapper);
    expect(payload?.xpubType).toBe(XpubKeyType.XPUB);
  });

  it('should emit detected-address when a plain BTC address is entered', async () => {
    wrapper = createWrapper(Blockchain.BTC);
    await setXpubValue(BTC_ADDRESS);

    const detected = wrapper.emitted('detected-address');
    expect(detected).toBeDefined();
    expect(detected?.at(-1)).toEqual([BTC_ADDRESS]);
    expect(wrapper.find('[data-cy="xpub-disambiguation"]').exists()).toBe(false);
  });
});
