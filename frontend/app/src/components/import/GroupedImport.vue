<script setup lang="ts">
const { t } = useI18n();
const sources = [
  {
    identifier: 'cointracking.info',
    name: t('import_data.cointracking.name'),
    logo: './assets/images/protocols/cointracking.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/CointrackingImport.vue')
    )
  },
  {
    identifier: 'cryptocom',
    name: t('import_data.cryptocom.name'),
    logo: './assets/images/protocols/crypto_com.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/CryptoComImport.vue')
    )
  },
  {
    identifier: 'blockfi',
    name: t('import_data.blockfi.name'),
    logo: './assets/images/protocols/blockfi.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BlockFiImport.vue')
    )
  },
  {
    identifier: 'nexo',
    name: t('import_data.nexo.name'),
    logo: './assets/images/protocols/nexo.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/NexoImport.vue')
    )
  },
  {
    identifier: 'shapeshift-trades',
    name: t('import_data.shapeshift.name'),
    logo: './assets/images/protocols/shapeshift.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/ShapeshiftImport.vue')
    )
  },
  {
    identifier: 'uphold',
    name: t('import_data.uphold.name'),
    logo: './assets/images/protocols/uphold.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/UpholdImport.vue')
    )
  },
  {
    identifier: 'bitmex',
    name: t('import_data.bitmex.name'),
    logo: './assets/images/protocols/bitmex.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BitMEXImport.vue')
    )
  },
  {
    identifier: 'bittrex',
    name: t('import_data.bittrex.name'),
    logo: './assets/images/protocols/bittrex.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BittrexImport.vue')
    )
  },
  {
    identifier: 'bisq',
    name: t('import_data.bisq.name'),
    logo: './assets/images/protocols/bisq.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BisqImport.vue')
    )
  },
  {
    identifier: 'binance',
    name: t('import_data.binance.name'),
    logo: './assets/images/protocols/binance.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BinanceImport.vue')
    )
  },
  {
    identifier: 'bitcoin_tax',
    name: t('import_data.bitcoin_tax.name'),
    logo: './assets/images/protocols/bitcointax.png',
    form: defineAsyncComponent(
      () => import('@/components/import/BitcoinImport.vue')
    )
  },
  {
    identifier: 'bitstamp',
    name: t('import_data.bitstamp.name'),
    logo: './assets/images/protocols/bitstamp.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BitstampImport.vue')
    )
  },
  {
    identifier: 'custom',
    name: t('import_data.custom.name'),
    icon: 'file-text-line',
    form: defineAsyncComponent(
      () => import('@/components/import/CustomImport.vue')
    )
  }
];

const selectedSource = ref<string>('');

const form = computed(
  () => sources.find(source => source.identifier === get(selectedSource))?.form
);
</script>

<template>
  <RuiCard>
    <div class="p-1 pt-2">
      <VSelect
        v-model="selectedSource"
        :label="t('import_data.select_source.title')"
        outlined
        :items="sources"
        item-value="identifier"
        item-text="name"
        :hide-details="true"
      >
        <template v-for="slotName in ['item', 'selection']" #[slotName]="data">
          <div v-if="data.item" :key="slotName" class="flex items-center gap-3">
            <AdaptiveWrapper>
              <AppImage
                v-if="data.item.logo"
                :src="data.item.logo"
                size="1.875rem"
                contain
              />
              <RuiIcon
                v-else-if="data.item.icon"
                size="30"
                class="text-rui-light-text-secondary"
                :name="data.item.icon"
              />
            </AdaptiveWrapper>
            {{ data.item.name }}
          </div>
        </template>
      </VSelect>

      <div v-if="form" class="mt-8">
        <Component :is="form" />
      </div>
    </div>
  </RuiCard>
</template>
