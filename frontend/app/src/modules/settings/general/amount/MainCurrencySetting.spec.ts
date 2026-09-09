import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { Currency } from '@/modules/assets/amount-display/currencies';
import MainCurrencySetting from '@/modules/settings/general/amount/MainCurrencySetting.vue';

const { model, writeError, writeSuccess } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  const { Currency: CurrencyClass } = await import('@/modules/assets/amount-display/currencies');
  return {
    model: ref(new CurrencyClass('US Dollar', 'USD', '$')),
    writeError: ref<string>(''),
    writeSuccess: ref<boolean>(false),
  };
});

vi.mock('@/modules/settings/use-setting-model', () => ({
  useSettingModel: (): Record<string, unknown> => ({ error: writeError, model, success: writeSuccess }),
}));

/** Renders the item slot for every option, so the per-item template is exercised. */
const RuiMenuSelectStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue', 'options', 'successMessages', 'errorMessages'],
  template: `<div>
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <span class="error">{{ errorMessages }}</span>
    <template v-for="item in options" :key="item.tickerSymbol">
      <slot name="item" :item="item" />
    </template>
  </div>`,
});

function createWrapper(): VueWrapper<any> {
  return mount(MainCurrencySetting, {
    global: { stubs: { RuiMenuSelect: RuiMenuSelectStub } },
  });
}

function select(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(RuiMenuSelectStub);
}

async function choose(wrapper: VueWrapper<any>, ticker: string): Promise<void> {
  select(wrapper).vm.$emit('update:modelValue', ticker);
  await nextTick();
}

/** The font size the avatar of one currency renders at. */
function avatarFontSize(wrapper: VueWrapper<any>, ticker: string): string | undefined {
  return wrapper.find(`#currency__${ticker.toLocaleLowerCase()} .font-bold`).attributes('style');
}

describe('mainCurrencySetting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(model, new Currency('US Dollar', 'USD', '$'));
    set(writeError, '');
    set(writeSuccess, false);
  });

  /**
   * The setting holds a whole currency object while the select speaks ticker symbols, so the
   * mapping has to hold in both directions or a change writes the wrong shape.
   */
  describe('the currency, stored as an object and selected by ticker', () => {
    it('should show the stored currency by its ticker', () => {
      set(model, new Currency('Euro', 'EUR', '€'));

      expect(select(createWrapper()).props('modelValue')).toBe('EUR');
    });

    it('should store the whole currency the chosen ticker names', async () => {
      const wrapper = createWrapper();

      await choose(wrapper, 'JPY');

      expect(get(model)).toMatchObject({ name: 'currencies.jpy', tickerSymbol: 'JPY', unicodeSymbol: '¥' });
    });

    it('should leave the setting alone when the ticker names no currency', async () => {
      const wrapper = createWrapper();

      await choose(wrapper, 'XXX');

      expect(get(model).tickerSymbol).toBe('USD');
    });

    it('should follow the setting changing elsewhere', async () => {
      const wrapper = createWrapper();

      set(model, new Currency('Swiss Franc', 'CHF', 'CHF'));
      await nextTick();

      expect(select(wrapper).props('modelValue')).toBe('CHF');
    });
  });

  describe('reporting the write', () => {
    it('should name the currency it saved', async () => {
      const wrapper = createWrapper();

      set(writeSuccess, true);
      await nextTick();

      expect(select(wrapper).props('successMessages'))
        .toContain('general_settings.validation.currency.success');
    });

    it('should report a failed write', async () => {
      const wrapper = createWrapper();

      set(writeError, 'the backend said no');
      await nextTick();

      expect(select(wrapper).props('errorMessages'))
        .toContain('general_settings.validation.currency.error: the backend said no');
    });

    it('should drop the message once the setting changes again', async () => {
      const wrapper = createWrapper();
      set(writeError, 'the backend said no');
      await nextTick();

      set(model, new Currency('Euro', 'EUR', '€'));
      await nextTick();

      expect(select(wrapper).props('errorMessages')).toBe('');
    });
  });

  /** A long symbol such as CHF has to shrink, or it overflows the avatar the short ones fill. */
  describe('the avatar symbol', () => {
    it('should render a one-character symbol at full size', () => {
      expect(avatarFontSize(createWrapper(), 'USD')).toBe('font-size: 2em;');
    });

    it('should shrink a three-character symbol', () => {
      expect(avatarFontSize(createWrapper(), 'CHF')).toBe('font-size: 1.2em;');
    });
  });
});
