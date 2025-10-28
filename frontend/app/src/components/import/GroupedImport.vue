<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { ImportSource } from '@/types/upload-types';
import AppImage from '@/components/common/AppImage.vue';
import { getPublicProtocolImagePath } from '@/utils/file';

const { t } = useI18n({ useScope: 'global' });

const sources = computed<ImportSource[]>(() => [
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/CointrackingImport.vue'))),
    key: 'cointracking.info',
    label: t('import_data.cointracking.name'),
    logo: getPublicProtocolImagePath('cointracking.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/CryptoComImport.vue'))),
    key: 'cryptocom',
    label: t('import_data.cryptocom.name'),
    logo: getPublicProtocolImagePath('crypto_com.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BlockFiImport.vue'))),
    key: 'blockfi',
    label: t('import_data.blockfi.name'),
    logo: getPublicProtocolImagePath('blockfi.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/NexoImport.vue'))),
    key: 'nexo',
    label: t('import_data.nexo.name'),
    logo: getPublicProtocolImagePath('nexo.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/ShapeshiftImport.vue'))),
    key: 'shapeshift-trades',
    label: t('import_data.shapeshift.name'),
    logo: getPublicProtocolImagePath('shapeshift.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/UpholdImport.vue'))),
    key: 'uphold',
    label: t('import_data.uphold.name'),
    logo: getPublicProtocolImagePath('uphold.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BitMexImport.vue'))),
    key: 'bitmex',
    label: t('import_data.bitmex.name'),
    logo: getPublicProtocolImagePath('bitmex.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BittrexImport.vue'))),
    key: 'bittrex',
    label: t('import_data.bittrex.name'),
    logo: getPublicProtocolImagePath('bittrex.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BisqImport.vue'))),
    key: 'bisq',
    label: t('import_data.bisq.name'),
    logo: getPublicProtocolImagePath('bisq.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BinanceImport.vue'))),
    key: 'binance',
    label: t('import_data.binance.name'),
    logo: getPublicProtocolImagePath('binance.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BitcoinImport.vue'))),
    key: 'bitcoin_tax',
    label: t('import_data.bitcoin_tax.name'),
    logo: getPublicProtocolImagePath('bitcointax.png'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BitstampImport.vue'))),
    key: 'bitstamp',
    label: t('import_data.bitstamp.name'),
    logo: getPublicProtocolImagePath('bitstamp.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/KucoinImport.vue'))),
    key: 'kucoin',
    label: t('import_data.kucoin.name'),
    logo: getPublicProtocolImagePath('kucoin.svg'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BlockpitImport.vue'))),
    key: 'blockpit',
    label: t('import_data.blockpit.name'),
    logo: getPublicProtocolImagePath('blockpit.png'),
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/CustomImport.vue'))),
    icon: 'lu-file-text',
    key: 'custom',
    label: t('import_data.custom.name'),
  },
]);

const selectedSource = ref<ImportSource>();

const [DefineDisplay, ReuseDisplay] = createReusableTemplate<{
  logo?: string;
  icon?: RuiIcons;
  label: string;
}>();
</script>

<template>
  <RuiCard content-class="p-1 pt-2">
    <DefineDisplay #default="{ logo, icon, label }">
      <div class="flex items-center gap-3">
        <AppImage
          v-if="logo"
          :src="logo"
          size="1.5rem"
          contain
          class="icon-bg"
        />
        <RuiIcon
          v-else-if="icon"
          size="28"
          class="text-rui-light-text-secondary icon-bg !p-1"
          :name="icon"
        />
        {{ label }}
      </div>
    </DefineDisplay>
    <RuiAutoComplete
      v-model="selectedSource"
      :label="t('import_data.select_source.title')"
      :append-width="1.75"
      :options="sources"
      text-attr="label"
      hide-details
      return-object
      auto-select-first
      variant="outlined"
      key-attr="key"
    >
      <template #selection="{ item }">
        <ReuseDisplay v-bind="item" />
      </template>
      <template #item="{ item }">
        <ReuseDisplay v-bind="item" />
      </template>
    </RuiAutoComplete>
    <div
      v-if="selectedSource"
      class="mt-8"
    >
      <Component :is="selectedSource.form" />
    </div>
  </RuiCard>
</template>
