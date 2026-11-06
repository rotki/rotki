import type { usePurgeData } from '@/modules/settings/data-security/data-management/use-purge-data';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { Purgeable } from '@/modules/session/purge';
import PurgeData from './PurgeData.vue';

const { modelSource, purge, purgeQuestion } = await vi.hoisted(async () => {
  const [{ Purgeable }, { computed, ref }] = await Promise.all([
    import('@/modules/session/purge'),
    import('vue'),
  ]);
  return {
    modelSource: ref<Purgeable>(Purgeable.CENTRALIZED_EXCHANGES),
    purge: vi.fn<(source: Purgeable) => Promise<void>>(async () => {}),
    purgeQuestion: computed<ConfirmQuestion>(() => ({
      confirmLabel: 'Purge data',
      message: 'Purge poloniex?\n\nOlder trades are lost.',
      title: 'Confirm purge',
      tone: 'error',
    })),
  };
});

vi.mock('@/modules/settings/data-security/data-management/use-purge-data', () => ({
  usePurgeData: (): Partial<ReturnType<typeof usePurgeData>> => ({
    centralizedExchangePurgeTypeOptions: computed(() => []),
    chainsSelection: computed<string[]>(() => []),
    csvImportLocations: computed<string[]>(() => ['binance', 'kraken']),
    exchanges: ref<string[]>([]),
    modelCentralizedExchange: ref<string>(''),
    modelCentralizedExchangeDataType: ref<'all'>('all'),
    modelChain: ref<string>(''),
    modelCsvImportLocation: ref<string>(''),
    modelDecentralizedExchange: ref<string>(''),
    modelModule: ref<string>(''),
    modelSource,
    pending: ref<boolean>(false),
    purge,
    purgeable: [{ id: Purgeable.CSV_IMPORTS, text: 'CSV Imports' }],
    purgeableModules: [],
    purgeQuestion,
    status: ref(null),
  }),
}));

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = {
  name: 'RuiMenu',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
};

function createWrapper(): VueWrapper<InstanceType<typeof PurgeData>> {
  return mount(PurgeData, {
    global: {
      stubs: {
        ActionStatusIndicator: true,
        ChainSelect: true,
        DefiModuleSelector: true,
        LocationSelector: true,
        RuiAutoComplete: true,
        RuiMenu,
        SettingsItem: { template: '<div><slot /></div>' },
      },
    },
  });
}

describe('purgeData', () => {
  beforeEach(() => {
    purge.mockClear();
    set(modelSource, Purgeable.CENTRALIZED_EXCHANGES);
  });

  it('should ask beside the button, with both paragraphs, before purging', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=purge-submit]').trigger('click');

    const question = wrapper.find('[data-testid=inline-confirm]');
    expect(question.text()).toContain('Purge poloniex?');
    expect(question.text()).toContain('Older trades are lost.');
    expect(purge).not.toHaveBeenCalled();
  });

  it('should purge the selected source once accepted', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=purge-submit]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(purge).toHaveBeenCalledExactlyOnceWith(Purgeable.CENTRALIZED_EXCHANGES);
  });

  it('should not purge when cancelled', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=purge-submit]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

    expect(purge).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
  });

  it('should offer only locations containing CSV-imported events', async () => {
    const wrapper = createWrapper();

    set(modelSource, Purgeable.CSV_IMPORTS);
    await nextTick();

    expect(wrapper.findComponent(LocationSelector).props('items')).toEqual(['binance', 'kraken']);
  });
});
