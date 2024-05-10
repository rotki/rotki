<script setup lang="ts">
import type { ImportSource } from '@/types/upload-types';

const { t } = useI18n();

const sources = computed<ImportSource[]>(() => [
  {
    key: 'cointracking.info',
    label: t('import_data.cointracking.name'),
    logo: './assets/images/protocols/cointracking.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/CointrackingImport.vue'),
    ),
  },
  {
    key: 'cryptocom',
    label: t('import_data.cryptocom.name'),
    logo: './assets/images/protocols/crypto_com.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/CryptoComImport.vue'),
    ),
  },
  {
    key: 'blockfi',
    label: t('import_data.blockfi.name'),
    logo: './assets/images/protocols/blockfi.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BlockFiImport.vue'),
    ),
  },
  {
    key: 'nexo',
    label: t('import_data.nexo.name'),
    logo: './assets/images/protocols/nexo.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/NexoImport.vue'),
    ),
  },
  {
    key: 'shapeshift-trades',
    label: t('import_data.shapeshift.name'),
    logo: './assets/images/protocols/shapeshift.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/ShapeshiftImport.vue'),
    ),
  },
  {
    key: 'uphold',
    label: t('import_data.uphold.name'),
    logo: './assets/images/protocols/uphold.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/UpholdImport.vue'),
    ),
  },
  {
    key: 'bitmex',
    label: t('import_data.bitmex.name'),
    logo: './assets/images/protocols/bitmex.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BitMexImport.vue'),
    ),
  },
  {
    key: 'bittrex',
    label: t('import_data.bittrex.name'),
    logo: './assets/images/protocols/bittrex.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BittrexImport.vue'),
    ),
  },
  {
    key: 'bisq',
    label: t('import_data.bisq.name'),
    logo: './assets/images/protocols/bisq.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BisqImport.vue'),
    ),
  },
  {
    key: 'binance',
    label: t('import_data.binance.name'),
    logo: './assets/images/protocols/binance.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BinanceImport.vue'),
    ),
  },
  {
    key: 'bitcoin_tax',
    label: t('import_data.bitcoin_tax.name'),
    logo: './assets/images/protocols/bitcointax.png',
    form: defineAsyncComponent(
      () => import('@/components/import/BitcoinImport.vue'),
    ),
  },
  {
    key: 'bitstamp',
    label: t('import_data.bitstamp.name'),
    logo: './assets/images/protocols/bitstamp.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BitstampImport.vue'),
    ),
  },
  {
    key: 'kucoin',
    label: t('import_data.kucoin.name'),
    logo: './assets/images/protocols/kucoin.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/KucoinImport.vue'),
    ),
  },
  {
    key: 'custom',
    label: t('import_data.custom.name'),
    icon: 'file-text-line',
    form: defineAsyncComponent(
      () => import('@/components/import/CustomImport.vue'),
    ),
  },
]);

const selectedSource = ref<ImportSource | null>(null);

const [DefineIcon, ReuseIcon] = createReusableTemplate<{
  logo: string;
  icon: string;
}>();
</script>

<template>
  <RuiCard>
    <div class="p-1 pt-2">
      <DefineIcon #default="{ logo, icon }">
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
      </DefineIcon>
      <RuiMenuSelect
        v-model="selectedSource"
        :label="t('import_data.select_source.title')"
        :append-width="1.75"
        :options="sources"
        full-width
        variant="outlined"
      >
        <template #activator.text="{ value: { logo, icon, label } }">
          <div class="flex items-center gap-3">
            <ReuseIcon v-bind="{ logo, icon }" />
            {{ label }}
          </div>
        </template>
        <template #item.prepend="{ option: { logo, icon } }">
          <ReuseIcon v-bind="{ logo, icon }" />
        </template>
      </RuiMenuSelect>
      <div
        v-if="selectedSource"
        class="mt-8"
      >
        <Component :is="selectedSource.form" />
      </div>
    </div>
  </RuiCard>
</template>
