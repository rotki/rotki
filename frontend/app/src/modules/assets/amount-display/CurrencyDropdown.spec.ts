import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { Currency } from '@/modules/assets/amount-display/currencies';
import CurrencyDropdown from '@/modules/assets/amount-display/CurrencyDropdown.vue';

const { currency, onCurrencyUpdate, update } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    currency: ref<{ tickerSymbol: string; unicodeSymbol: string }>({ tickerSymbol: 'USD', unicodeSymbol: '$' }),
    onCurrencyUpdate: vi.fn(async () => {}),
    update: vi.fn(async () => ({ success: true })),
  };
});

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): Record<string, unknown> => ({ update }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): typeof currency => currency,
}));

vi.mock('@/modules/assets/prices/use-currency-update', () => ({
  useCurrencyUpdate: (): Record<string, unknown> => ({ onCurrencyUpdate }),
}));

const MenuStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue'],
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
});

const TextFieldStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue'],
  template: '<input @keyup.enter="$emit(\'keyup\', $event)" />',
});

function createWrapper(): VueWrapper<any> {
  return mount(CurrencyDropdown, {
    global: {
      stubs: {
        /** No `@click` of its own: the parent's listener already falls through onto the root. */
        ListItem: {
          props: ['title', 'subtitle'],
          template: '<div class="currency">{{ title }}<slot name="avatar" /></div>',
        },
        MenuTooltipButton: true,
        RuiMenu: MenuStub,
        RuiTextField: TextFieldStub,
      },
    },
  });
}

function listed(wrapper: VueWrapper<any>): string[] {
  return wrapper.findAll('.currency').map(node => node.text().replace(/[^\w\s()]+$/u, '').trim());
}

async function type(wrapper: VueWrapper<any>, value: string): Promise<void> {
  wrapper.findComponent(TextFieldStub).vm.$emit('update:modelValue', value);
  await nextTick();
}

async function pick(wrapper: VueWrapper<any>, index: number): Promise<void> {
  await wrapper.findAll('.currency')[index].trigger('click');
  await flushPromises();
}

describe('currencyDropdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    set(currency, new Currency('US Dollar', 'USD', '$'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('filtering', () => {
    it('should offer every currency while nothing is typed', () => {
      expect(listed(createWrapper()).length).toBeGreaterThan(10);
    });

    it('should match on the ticker symbol', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'gbp');

      expect(listed(wrapper)).toEqual(['currencies.gbp']);
    });

    /** The names are translated, so a user typing what they read has to match on them too. */
    it('should match on the name', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'currencies.eur');

      expect(listed(wrapper)).toEqual(['currencies.eur']);
    });

    it('should match regardless of case', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'GBP');

      expect(listed(wrapper)).toEqual(['currencies.gbp']);
    });

    it('should offer nothing when nothing matches', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'nonsense');

      expect(listed(wrapper)).toEqual([]);
    });
  });

  describe('picking a currency', () => {
    it('should save it and re-read the prices', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'gbp');

      await pick(wrapper, 0);

      expect(update).toHaveBeenCalledWith({ mainCurrency: 'GBP' });
      expect(onCurrencyUpdate).toHaveBeenCalledTimes(1);
    });

    /** Re-picking the current currency changes nothing, so it is not worth a write or a re-read. */
    it('should do nothing when it is already the current one', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'usd');

      await pick(wrapper, 0);

      expect(update).not.toHaveBeenCalled();
      expect(onCurrencyUpdate).not.toHaveBeenCalled();
    });

    it('should close the menu either way', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'usd');

      await pick(wrapper, 0);

      expect(wrapper.findComponent(MenuStub).props('modelValue')).toBe(false);
    });
  });

  /** Reopening the menu on the last search would hide most of the list without saying why. */
  it('should forget the filter when the menu closes', async () => {
    const wrapper = createWrapper();
    await type(wrapper, 'gbp');

    wrapper.findComponent(MenuStub).vm.$emit('update:modelValue', true);
    await nextTick();
    wrapper.findComponent(MenuStub).vm.$emit('update:modelValue', false);
    await nextTick();

    expect(listed(wrapper).length).toBeGreaterThan(10);
  });

  /** A longer symbol has to shrink, or it overflows the avatar the short ones fill. */
  describe('the symbol size', () => {
    function fontSizeOf(wrapper: VueWrapper<any>, ticker: string): string | undefined {
      const item = wrapper.findAll('.currency').find(node => node.text().includes(`currencies.${ticker}`));
      assert(item);
      return item.find('.font-bold').attributes('style');
    }

    it('should render a one-character symbol at full size', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'usd');

      expect(fontSizeOf(wrapper, 'usd')).toBe('font-size: 2em;');
    });

    it('should shrink a three-character symbol', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'chf');

      expect(fontSizeOf(wrapper, 'chf')).toBe('font-size: 1.2em;');
    });
  });
});
