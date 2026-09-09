import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { Defaults } from '@/modules/core/common/defaults';
import InternalTxConflictRepullSettings from '@/modules/settings/general/InternalTxConflictRepullSettings.vue';
import { createRuiPlugin } from '@/plugins/rui';

const {
  batchModel,
  batchWriteError,
  batchWriteSuccess,
  flushBatch,
  flushFrequency,
  frequencyModel,
  frequencyWriteError,
  frequencyWriteSuccess,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    batchModel: ref<number>(20),
    batchWriteError: ref<string>(''),
    batchWriteSuccess: ref<boolean>(false),
    flushBatch: vi.fn(async () => {}),
    flushFrequency: vi.fn(async () => {}),
    frequencyModel: ref<number>(3600),
    frequencyWriteError: ref<string>(''),
    frequencyWriteSuccess: ref<boolean>(false),
  };
});

vi.mock('@/modules/settings/use-setting-model', () => ({
  useSettingModel: (key: string): Record<string, unknown> =>
    key === 'internalTxsToRepull'
      ? { error: batchWriteError, flush: flushBatch, model: batchModel, success: batchWriteSuccess }
      : { error: frequencyWriteError, flush: flushFrequency, model: frequencyModel, success: frequencyWriteSuccess },
}));

function createWrapper(): VueWrapper<any> {
  return mount(InternalTxConflictRepullSettings, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        SettingResetConfirmButton: {
          emits: ['confirm'],
          name: 'SettingResetConfirmButton',
          props: ['compact'],
          template: '<button @click="$emit(\'confirm\')" />',
        },
        SettingsItem: { name: 'SettingsItem', template: '<div><slot /></div>' },
      },
    },
  });
}

/**
 * The two fields are the same component, so they are told apart by their test id.
 *
 * @remarks
 * A string selector would resolve `findComponent` to its `WrapperLike` overload, which carries
 * neither `props` nor `vm`.
 */
function field(wrapper: VueWrapper<any>, which: 'batch-size' | 'frequency'): VueWrapper<any> {
  const found = wrapper
    .findAllComponents({ name: 'RuiTextField' })
    .find(component => component.attributes('data-testid') === `internal-tx-${which}`);
  assert(found);
  return found;
}

function resetButton(wrapper: VueWrapper<any>, which: 'batch-size' | 'frequency'): ReturnType<VueWrapper<any>['find']> {
  return wrapper.find(`[data-testid=internal-tx-${which}-reset]`);
}

async function type(wrapper: VueWrapper<any>, which: 'batch-size' | 'frequency', value: string): Promise<void> {
  await field(wrapper, which).vm.$emit('update:modelValue', value);
  await nextTick();
}

describe('internalTxConflictRepullSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(batchModel, 20);
    set(batchWriteError, '');
    set(batchWriteSuccess, false);
    set(frequencyModel, 3600);
    set(frequencyWriteError, '');
  });

  /**
   * The setting is stored in seconds and shown in minutes, so the conversion has to hold in both
   * directions or the value drifts by a factor of sixty every round trip.
   */
  describe('the frequency, stored in seconds and shown in minutes', () => {
    it('should show the stored seconds as minutes', () => {
      set(frequencyModel, 3600);

      expect(field(createWrapper(), 'frequency').props('modelValue')).toBe('60');
    });

    it('should store the entered minutes as seconds', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'frequency', '30');

      expect(get(frequencyModel)).toBe(1800);
    });

    it('should keep a half minute rather than rounding it away', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'frequency', '0.5');

      expect(get(frequencyModel)).toBe(30);
    });

    it('should follow the setting changing elsewhere', async () => {
      const wrapper = createWrapper();

      set(frequencyModel, 900);
      await nextTick();

      expect(field(wrapper, 'frequency').props('modelValue')).toBe('15');
    });
  });

  describe('the batch size, which needs no conversion', () => {
    it('should show the stored value', () => {
      set(batchModel, 42);

      expect(field(createWrapper(), 'batch-size').props('modelValue')).toBe('42');
    });

    it('should store what was entered', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'batch-size', '75');

      expect(get(batchModel)).toBe(75);
    });

    it('should follow the setting changing elsewhere', async () => {
      const wrapper = createWrapper();

      set(batchModel, 5);
      await nextTick();

      expect(field(wrapper, 'batch-size').props('modelValue')).toBe('5');
    });
  });

  /** An emptied field is the user mid-edit, not a request to store nothing. */
  describe('while a field is empty', () => {
    it('should leave the batch size alone', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'batch-size', '');

      expect(get(batchModel)).toBe(20);
    });

    it('should leave the frequency alone', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'frequency', '');

      expect(get(frequencyModel)).toBe(3600);
    });
  });

  /** A reset is a deliberate act, so it is written immediately rather than on the debounce. */
  describe('resetting to the default', () => {
    it('should restore the default batch size and write it at once', async () => {
      set(batchModel, 99);
      const wrapper = createWrapper();

      await resetButton(wrapper, 'batch-size').trigger('click');

      expect(get(batchModel)).toBe(Defaults.DEFAULT_INTERNAL_TXS_TO_REPULL);
      expect(flushBatch).toHaveBeenCalledTimes(1);
    });

    it('should restore the default frequency and write it at once', async () => {
      set(frequencyModel, 60);
      const wrapper = createWrapper();

      await resetButton(wrapper, 'frequency').trigger('click');

      expect(get(frequencyModel)).toBe(Defaults.DEFAULT_INTERNAL_TX_CONFLICT_REPULL_FREQUENCY);
      expect(flushFrequency).toHaveBeenCalledTimes(1);
    });
  });

  describe('reporting a failed write', () => {
    it('should name the field the batch size write failed on', async () => {
      const wrapper = createWrapper();

      set(batchWriteError, 'the backend said no');
      await nextTick();

      expect(field(wrapper, 'batch-size').props('errorMessages'))
        .toContain('general_settings.history_event.internal_tx_conflicts.batch_size.error: the backend said no');
    });

    it('should name the field the frequency write failed on', async () => {
      const wrapper = createWrapper();

      set(frequencyWriteError, 'the backend said no');
      await nextTick();

      expect(field(wrapper, 'frequency').props('errorMessages'))
        .toContain('general_settings.history_event.internal_tx_conflicts.frequency.error: the backend said no');
    });
  });
});
