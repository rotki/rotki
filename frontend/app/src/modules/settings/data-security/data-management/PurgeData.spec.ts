import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { Purgeable } from '@/modules/session/purge';
import PurgeData from '@/modules/settings/data-security/data-management/PurgeData.vue';

const { modelSource } = await vi.hoisted(async () => {
  const [{ Purgeable }, { ref }] = await Promise.all([
    import('@/modules/session/purge'),
    import('vue'),
  ]);
  return { modelSource: ref<Purgeable>(Purgeable.TRANSACTIONS) };
});

vi.mock('@/modules/settings/data-security/data-management/use-purge-data', async () => {
  const { ref } = await import('vue');
  return {
    usePurgeData: (): object => ({
      centralizedExchangePurgeTypeOptions: ref([]),
      chainsSelection: ref([]),
      csvImportLocations: ref(['binance', 'kraken']),
      exchanges: ref([]),
      modelCentralizedExchange: ref(''),
      modelCentralizedExchangeDataType: ref('all'),
      modelChain: ref(''),
      modelCsvImportLocation: ref(''),
      modelDecentralizedExchange: ref(''),
      modelModule: ref(''),
      modelSource,
      pending: ref(false),
      purgeable: [{ id: 'csv_imports', text: 'CSV Imports' }],
      purgeableModules: [],
      showConfirmation: vi.fn(),
      status: ref(null),
    }),
  };
});

describe('purge data', () => {
  it('should offer only locations containing CSV-imported events', async () => {
    const wrapper = mount(PurgeData, {
      global: {
        stubs: {
          ActionStatusIndicator: true,
          ChainSelect: true,
          DefiModuleSelector: true,
          LocationSelector: true,
          RuiAutoComplete: true,
          SettingsItem: { template: '<div><slot /></div>' },
        },
      },
    });

    set(modelSource, Purgeable.CSV_IMPORTS);
    await nextTick();

    expect(wrapper.findComponent(LocationSelector).props('items')).toEqual(['binance', 'kraken']);
  });
});
