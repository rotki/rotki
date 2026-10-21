<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { ImportSource } from '@/modules/core/common/upload-types';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import IconMark from '@/modules/shell/components/IconMark.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();

const sources = computed<ImportSource[]>(() => [
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/CointrackingImport.vue'))),
    key: 'cointracking.info',
    label: t('import_data.cointracking.name'),
    logo: getPublicProtocolImagePath('cointracking.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/CoinledgerImport.vue'))),
    logo: getPublicProtocolImagePath('coinledger.png'),
    key: 'coinledger',
    label: t('import_data.coinledger.name'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/CryptoComImport.vue'))),
    key: 'cryptocom',
    label: t('import_data.cryptocom.name'),
    logo: getPublicProtocolImagePath('crypto_com.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/BlockFiImport.vue'))),
    key: 'blockfi',
    label: t('import_data.blockfi.name'),
    logo: getPublicProtocolImagePath('blockfi.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/NexoImport.vue'))),
    key: 'nexo',
    label: t('import_data.nexo.name'),
    logo: getPublicProtocolImagePath('nexo.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/ShapeshiftImport.vue'))),
    key: 'shapeshift-trades',
    label: t('import_data.shapeshift.name'),
    logo: getPublicProtocolImagePath('shapeshift.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/UpholdImport.vue'))),
    key: 'uphold',
    label: t('import_data.uphold.name'),
    logo: getPublicProtocolImagePath('uphold.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/BitMexImport.vue'))),
    key: 'bitmex',
    label: t('import_data.bitmex.name'),
    logo: getPublicProtocolImagePath('bitmex.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/BittrexImport.vue'))),
    key: 'bittrex',
    label: t('import_data.bittrex.name'),
    logo: getPublicProtocolImagePath('bittrex.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/BisqImport.vue'))),
    key: 'bisq',
    label: t('import_data.bisq.name'),
    logo: getPublicProtocolImagePath('bisq.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/BinanceImport.vue'))),
    key: 'binance',
    label: t('import_data.binance.name'),
    logo: getPublicProtocolImagePath('binance.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/BitcoinImport.vue'))),
    key: 'bitcoin_tax',
    label: t('import_data.bitcoin_tax.name'),
    logo: getPublicProtocolImagePath('bitcointax.png'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/BitstampImport.vue'))),
    key: 'bitstamp',
    label: t('import_data.bitstamp.name'),
    logo: getPublicProtocolImagePath('bitstamp.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/KucoinImport.vue'))),
    key: 'kucoin',
    label: t('import_data.kucoin.name'),
    logo: getPublicProtocolImagePath('kucoin.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/BlockpitImport.vue'))),
    key: 'blockpit',
    label: t('import_data.blockpit.name'),
    logo: getPublicProtocolImagePath('blockpit.png'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/modules/user-data/CustomImport.vue'))),
    icon: 'lu-file-text',
    key: 'custom',
    label: t('import_data.custom.name'),
  },
]);

const selectedSource = ref<ImportSource>();

watch(route, ({ query }) => {
  if (typeof query.source !== 'string')
    return;

  const source = get(sources).find(({ key }) => key === query.source);
  if (source)
    set(selectedSource, source);
}, { immediate: true });

const [DefineDisplay, ReuseDisplay] = createReusableTemplate<{
  logo?: string;
  icon?: RuiIcons;
  label: string;
}>();
</script>

<template>
  <TablePageLayout :title="[t('import_data.title')]">
    <DefineDisplay #default="{ logo, icon, label }">
      <div class="flex items-center gap-3">
        <IconMark
          v-if="logo"
          :src="logo"
          size="1.5rem"
        />
        <RuiIcon
          v-else-if="icon"
          size="28"
          class="text-rui-light-text-secondary"
          :name="icon"
        />
        {{ label }}
      </div>
    </DefineDisplay>
    <template #buttons>
      <div class="w-full sm:w-72">
        <RuiAutoComplete
          v-model="selectedSource"
          :label="t('import_data.select_source.title')"
          label-placement="hidden"
          :placeholder="t('import_data.select_source.title')"
          :append-width="1.75"
          :options="sources"
          text-attr="label"
          dense
          details="hidden"
          return-object
          auto-select-first
          key-attr="key"
          data-testid="import-source-select"
        >
          <template #selection="{ item }">
            <ReuseDisplay v-bind="item" />
          </template>
          <template #item="{ item }">
            <ReuseDisplay v-bind="item" />
          </template>
        </RuiAutoComplete>
      </div>
      <HintMenuIcon :options="{ placement: 'left-start' }">
        {{ t('import_data.description') }}
      </HintMenuIcon>
    </template>

    <Component
      :is="selectedSource.form"
      v-if="selectedSource"
    />
    <section
      v-else
      class="flex flex-col gap-3 rounded-rui-card border border-rui-divider bg-rui-surface p-4"
    >
      <div class="text-sm text-rui-text-secondary">
        {{ t('import_data.select_source.hint') }}
      </div>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
        <button
          v-for="source in sources"
          :key="source.key"
          type="button"
          class="flex items-center gap-3 rounded-rui-control border border-rui-divider px-3 py-3 text-left text-sm font-medium text-rui-text transition-colors hover:border-rui-primary-border hover:bg-rui-primary-subtle focus-visible:outline-2 focus-visible:outline-rui-primary motion-reduce:transition-none"
          data-testid="import-source-tile"
          :data-key="source.key"
          @click="selectedSource = source"
        >
          <ReuseDisplay v-bind="source" />
        </button>
      </div>
    </section>
  </TablePageLayout>
</template>
