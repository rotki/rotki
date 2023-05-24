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
    identifier: 'custom',
    name: t('import_data.custom.name'),
    icon: 'mdi-book-open',
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
  <card>
    <div class="pa-1 pt-2">
      <v-select
        v-model="selectedSource"
        :label="t('import_data.select_source.title')"
        outlined
        :items="sources"
        item-value="identifier"
        item-text="name"
        :hide-details="true"
      >
        <template v-for="slotName in ['item', 'selection']" #[slotName]="data">
          <div v-if="data.item" :key="slotName" class="d-flex align-center">
            <adaptive-wrapper>
              <v-img
                v-if="data.item.logo"
                :src="data.item.logo"
                :width="30"
                :height="30"
                max-height="30px"
                max-width="30px"
                position="center left"
                contain
              />
              <v-icon
                v-else-if="data.item.icon"
                color="grey darken-2"
                size="30"
              >
                {{ data.item.icon }}
              </v-icon>
            </adaptive-wrapper>
            <div class="pl-3">{{ data.item.name }}</div>
          </div>
        </template>
      </v-select>

      <div v-if="form" class="mt-8">
        <component :is="form" />
      </div>
    </div>
  </card>
</template>
