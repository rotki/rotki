<script setup lang="ts">
import type { ImportSource } from '@/types/upload-types';
import type { RuiIcons } from '@rotki/ui-library';
import AppImage from '@/components/common/AppImage.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';

const { t } = useI18n();

const sources = computed<ImportSource[]>(() => [
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/CointrackingImport.vue'))),
    key: 'cointracking.info',
    label: t('import_data.cointracking.name'),
    logo: './assets/images/protocols/cointracking.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/CryptoComImport.vue'))),
    key: 'cryptocom',
    label: t('import_data.cryptocom.name'),
    logo: './assets/images/protocols/crypto_com.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BlockFiImport.vue'))),
    key: 'blockfi',
    label: t('import_data.blockfi.name'),
    logo: './assets/images/protocols/blockfi.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/NexoImport.vue'))),
    key: 'nexo',
    label: t('import_data.nexo.name'),
    logo: './assets/images/protocols/nexo.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/ShapeshiftImport.vue'))),
    key: 'shapeshift-trades',
    label: t('import_data.shapeshift.name'),
    logo: './assets/images/protocols/shapeshift.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/UpholdImport.vue'))),
    key: 'uphold',
    label: t('import_data.uphold.name'),
    logo: './assets/images/protocols/uphold.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BitMexImport.vue'))),
    key: 'bitmex',
    label: t('import_data.bitmex.name'),
    logo: './assets/images/protocols/bitmex.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BittrexImport.vue'))),
    key: 'bittrex',
    label: t('import_data.bittrex.name'),
    logo: './assets/images/protocols/bittrex.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BisqImport.vue'))),
    key: 'bisq',
    label: t('import_data.bisq.name'),
    logo: './assets/images/protocols/bisq.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BinanceImport.vue'))),
    key: 'binance',
    label: t('import_data.binance.name'),
    logo: './assets/images/protocols/binance.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BitcoinImport.vue'))),
    key: 'bitcoin_tax',
    label: t('import_data.bitcoin_tax.name'),
    logo: './assets/images/protocols/bitcointax.png',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BitstampImport.vue'))),
    key: 'bitstamp',
    label: t('import_data.bitstamp.name'),
    logo: './assets/images/protocols/bitstamp.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/KucoinImport.vue'))),
    key: 'kucoin',
    label: t('import_data.kucoin.name'),
    logo: './assets/images/protocols/kucoin.svg',
  },
  {
    form: markRaw(defineAsyncComponent(() => import('@/components/import/BlockpitImport.vue'))),
    key: 'blockpit',
    label: t('import_data.blockpit.name'),
    logo: './assets/images/protocols/blockpit.png',
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
        <AdaptiveWrapper
          padding="0"
          width="1.5rem"
          height="1.5rem"
        >
          <AppImage
            v-if="logo"
            :src="logo"
            size="1.5rem"
            contain
          />
          <RuiIcon
            v-else-if="icon"
            size="24"
            class="text-rui-light-text-secondary"
            :name="icon"
          />
        </AdaptiveWrapper>
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
