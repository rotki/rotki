import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import PriceRefresh from '@/modules/assets/prices/PriceRefresh.vue';
import PriceOracleSettings from '@/modules/settings/PriceOracleSettings.vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

interface SettingModelState {
  error: Ref<string>;
  model: Ref<string[]>;
  success: Ref<boolean>;
}

const { held, spies } = vi.hoisted(() => {
  const held: { models: Map<string, SettingModelState> } = { models: new Map() };
  return {
    held,
    spies: { reset: vi.fn<() => void>() },
  };
});

vi.mock('@/modules/settings/use-setting-model', () => ({
  useSettingModel: (key: string): SettingModelState | undefined => held.models.get(key),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): object => ({ reset: spies.reset }),
}));

function settingModel(value: string[]): SettingModelState {
  return { error: ref<string>(''), model: ref<string[]>(value), success: ref<boolean>(false) };
}

describe('priceOracleSettings', () => {
  let wrapper: VueWrapper<InstanceType<typeof PriceOracleSettings>>;
  let current: SettingModelState;
  let historic: SettingModelState;

  function createWrapper(): VueWrapper<InstanceType<typeof PriceOracleSettings>> {
    return mount(PriceOracleSettings, {
      global: {
        stubs: {
          PriceRefresh: true,
          PrioritizedList: {
            emits: ['update:modelValue'],
            name: 'PrioritizedList',
            props: ['modelValue', 'status'],
            template: '<div />',
          },
          RuiAlert: true,
          SettingCategoryHeader: true,
        },
      },
    });
  }

  function list(index: 0 | 1): VueWrapper {
    return wrapper.findAllComponents({ name: 'PrioritizedList' })[index];
  }

  function status(index: 0 | 1): { error: string; success: string } {
    const props: Record<string, unknown> = list(index).props();
    const value = props.status;
    assert(typeof value === 'object' && value !== null && 'error' in value && 'success' in value);
    return { error: String(value.error), success: String(value.success) };
  }

  beforeEach(() => {
    vi.clearAllMocks();
    current = settingModel([PriceOracle.COINGECKO, PriceOracle.DEFILLAMA]);
    historic = settingModel([PriceOracle.CRYPTOCOMPARE]);
    held.models = new Map([['currentPriceOracles', current], ['historicalPriceOracles', historic]]);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should clear the cached historical prices from the refresh button', async () => {
    wrapper = createWrapper();

    wrapper.findComponent(PriceRefresh).vm.$emit('click');

    expect(spies.reset).toHaveBeenCalledOnce();
  });

  describe('historical oracles', () => {
    it('should clear the cached historical prices once a new order is saved', async () => {
      wrapper = createWrapper();

      set(historic.success, true);
      await nextTick();

      expect(spies.reset).toHaveBeenCalledOnce();
      expect(status(1).success).toBe('settings.saved');
    });

    it('should keep only real oracles when the order changes', async () => {
      wrapper = createWrapper();

      list(1).vm.$emit('update:modelValue', [PriceOracle.DEFILLAMA, 'not_an_oracle', PriceOracle.COINGECKO]);

      expect(get(historic.model)).toEqual([PriceOracle.DEFILLAMA, PriceOracle.COINGECKO]);
    });

    it('should report an order that could not be saved', async () => {
      wrapper = createWrapper();

      set(historic.error, 'backend rejected the list');
      await nextTick();

      expect(status(1).error).toBe('settings.not_saved: backend rejected the list');
      expect(spies.reset).not.toHaveBeenCalled();
    });
  });

  describe('current oracles', () => {
    it('should confirm a saved order without touching the historical cache', async () => {
      wrapper = createWrapper();

      set(current.success, true);
      await nextTick();

      expect(status(0).success).toBe('settings.saved: price_oracle_settings.latest_prices_update');
      expect(spies.reset).not.toHaveBeenCalled();
    });

    it('should keep only real oracles when the order changes', async () => {
      wrapper = createWrapper();

      list(0).vm.$emit('update:modelValue', ['not_an_oracle', PriceOracle.UNISWAP3]);

      expect(get(current.model)).toEqual([PriceOracle.UNISWAP3]);
    });

    it('should drop the previous message once the order changes again', async () => {
      wrapper = createWrapper();
      set(current.error, 'backend rejected the list');
      await nextTick();

      list(0).vm.$emit('update:modelValue', [PriceOracle.COINGECKO]);
      await nextTick();

      expect(status(0).error).toBe('');
    });
  });

  describe('empty list warning', () => {
    it('should not warn while both lists have an oracle', () => {
      wrapper = createWrapper();

      expect(wrapper.findComponent({ name: 'RuiAlert' }).exists()).toBe(false);
    });

    it.each([
      ['current', (): void => set(current.model, [])],
      ['historical', (): void => set(historic.model, [])],
    ])('should warn once the %s list is empty', async (_name, empty) => {
      wrapper = createWrapper();

      empty();
      await nextTick();

      expect(wrapper.findComponent({ name: 'RuiAlert' }).exists()).toBe(true);
    });
  });
});
