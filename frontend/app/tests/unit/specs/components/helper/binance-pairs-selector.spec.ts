import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import BinancePairsSelector from '@/components/helper/BinancePairsSelector.vue';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { createClipboardEvent } from '../../../utils/events';

vi.mock('@/composables/api/balances/exchanges', () => ({
  useExchangeApi: vi.fn(),
}));

vi.mock('@shared/utils', () => ({
  backoff: vi.fn(async (_retries: number, fn: () => Promise<string[]>) => fn()),
}));

describe('components/helper/BinancePairsSelector.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof BinancePairsSelector>>;
  let queryBinanceMarketsMock: ReturnType<typeof vi.fn>;
  let queryBinanceUserMarketsMock: ReturnType<typeof vi.fn>;

  const allMarkets = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'LTCBTC', 'ETHBTC'];

  beforeEach(() => {
    setActivePinia(createPinia());

    queryBinanceMarketsMock = vi.fn().mockResolvedValue(allMarkets);
    queryBinanceUserMarketsMock = vi.fn().mockResolvedValue([]);

    (useExchangeApi as Mock).mockReturnValue({
      queryBinanceMarkets: queryBinanceMarketsMock,
      queryBinanceUserMarkets: queryBinanceUserMarketsMock,
    });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof BinancePairsSelector> = {}): VueWrapper<InstanceType<typeof BinancePairsSelector>> => mount(BinancePairsSelector, {
    props: {
      edit: false,
      location: 'binance',
      name: 'test-exchange',
    },
    ...options,
  });

  describe('paste functionality', () => {
    async function triggerPaste(inputWrapper: ReturnType<typeof wrapper.find>, text: string): Promise<void> {
      const event = createClipboardEvent(text);
      inputWrapper.element.dispatchEvent(event);
      await flushPromises();
    }

    it('should parse pasted pairs separated by commas', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const emitted = wrapper.emitted('update:selection');
      const initialEmitCount = emitted?.length ?? 0;

      const input = wrapper.find('.input-value');
      await triggerPaste(input, 'BTCUSDT, ETHUSDT, BNBUSDT');

      const newEmits = wrapper.emitted('update:selection')!;
      expect(newEmits.length).toBeGreaterThan(initialEmitCount);
      expect(newEmits.at(-1)).toEqual([['BTCUSDT', 'ETHUSDT', 'BNBUSDT']]);
    });

    it('should parse pasted pairs separated by spaces', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const emitted = wrapper.emitted('update:selection');
      const initialEmitCount = emitted?.length ?? 0;

      const input = wrapper.find('.input-value');
      await triggerPaste(input, 'BTCUSDT ETHUSDT');

      const newEmits = wrapper.emitted('update:selection')!;
      expect(newEmits.length).toBeGreaterThan(initialEmitCount);
      expect(newEmits.at(-1)).toEqual([['BTCUSDT', 'ETHUSDT']]);
    });

    it('should parse pasted pairs separated by newlines', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const emitted = wrapper.emitted('update:selection');
      const initialEmitCount = emitted?.length ?? 0;

      const input = wrapper.find('.input-value');
      await triggerPaste(input, 'BTCUSDT\nETHUSDT\nBNBUSDT');

      const newEmits = wrapper.emitted('update:selection')!;
      expect(newEmits.length).toBeGreaterThan(initialEmitCount);
      expect(newEmits.at(-1)).toEqual([['BTCUSDT', 'ETHUSDT', 'BNBUSDT']]);
    });

    it('should parse pasted pairs with mixed delimiters', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const emitted = wrapper.emitted('update:selection');
      const initialEmitCount = emitted?.length ?? 0;

      const input = wrapper.find('.input-value');
      await triggerPaste(input, 'BTCUSDT, ETHUSDT\nBNBUSDT LTCBTC');

      const newEmits = wrapper.emitted('update:selection')!;
      expect(newEmits.length).toBeGreaterThan(initialEmitCount);
      expect(newEmits.at(-1)).toEqual([['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'LTCBTC']]);
    });

    it('should show success alert when all pasted pairs are valid', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const input = wrapper.find('.input-value');
      await triggerPaste(input, 'BTCUSDT, ETHUSDT');

      const alert = wrapper.find('[data-testid="alert"]');
      expect(alert.exists()).toBe(true);
      expect(alert.attributes('data-type')).toBe('success');
    });

    it('should show warning alert when some pasted pairs are invalid', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const input = wrapper.find('.input-value');
      await triggerPaste(input, 'BTCUSDT, INVALID_PAIR');

      const alert = wrapper.find('[data-testid="alert"]');
      expect(alert.exists()).toBe(true);
      expect(alert.attributes('data-type')).toBe('warning');
    });

    it('should identify invalid pairs that are not in allMarkets', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const emitted = wrapper.emitted('update:selection');
      const initialEmitCount = emitted?.length ?? 0;

      const input = wrapper.find('.input-value');
      await triggerPaste(input, 'BTCUSDT, FAKEPAIR, INVALID');

      const newEmits = wrapper.emitted('update:selection')!;
      expect(newEmits.length).toBeGreaterThan(initialEmitCount);
      // Only BTCUSDT should be added as it's the only valid pair
      expect(newEmits.at(-1)).toEqual([['BTCUSDT']]);
    });

    it('should not add duplicate pairs to selection', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const input = wrapper.find('.input-value');

      // First paste
      await triggerPaste(input, 'BTCUSDT, ETHUSDT');

      const emitsAfterFirst = wrapper.emitted('update:selection')!;
      const selectionAfterFirst = emitsAfterFirst.at(-1)![0];
      expect(selectionAfterFirst).toEqual(['BTCUSDT', 'ETHUSDT']);

      // Second paste with same pairs
      await triggerPaste(input, 'BTCUSDT, ETHUSDT');

      const emitsAfterSecond = wrapper.emitted('update:selection')!;
      const selectionAfterSecond = emitsAfterSecond.at(-1)![0];
      // Selection should still have only 2 items (no duplicates)
      expect(selectionAfterSecond).toEqual(['BTCUSDT', 'ETHUSDT']);
    });

    it('should show success message for valid pairs even if already selected', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const input = wrapper.find('.input-value');

      // First paste
      await triggerPaste(input, 'BTCUSDT');

      // Second paste with same pair - should still show success
      await triggerPaste(input, 'BTCUSDT');

      const alert = wrapper.find('[data-testid="alert"]');
      expect(alert.exists()).toBe(true);
      expect(alert.attributes('data-type')).toBe('success');
    });

    it('should not show alert when pasting empty string', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const input = wrapper.find('.input-value');
      await triggerPaste(input, '');

      expect(wrapper.find('[data-testid="alert"]').exists()).toBe(false);
    });

    it('should not show alert when pasting only whitespace', async () => {
      wrapper = createWrapper();
      await flushPromises();

      const input = wrapper.find('.input-value');
      await triggerPaste(input, '   \n  \t  ');

      expect(wrapper.find('[data-testid="alert"]').exists()).toBe(false);
    });
  });

  describe('api interactions', () => {
    it('should fetch all markets on mount', async () => {
      wrapper = createWrapper();
      await flushPromises();

      expect(queryBinanceMarketsMock).toHaveBeenCalledWith('binance');
    });

    it('should fetch user markets on mount when in edit mode', async () => {
      wrapper = createWrapper({
        props: {
          edit: true,
          location: 'binance',
          name: 'test-exchange',
        },
      });
      await flushPromises();

      expect(queryBinanceUserMarketsMock).toHaveBeenCalledWith('test-exchange', 'binance');
    });

    it('should not fetch user markets when not in edit mode', async () => {
      wrapper = createWrapper({
        props: {
          edit: false,
          location: 'binance',
          name: 'test-exchange',
        },
      });
      await flushPromises();

      expect(queryBinanceUserMarketsMock).not.toHaveBeenCalled();
    });
  });
});
