<script setup lang="ts">
const { tc } = useI18n();
const sources = [
  {
    identifier: 'cointracking.info',
    name: tc('import_data.cointracking.name'),
    logo: './assets/images/cointracking.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/CointrackingImport.vue')
    )
  },
  {
    identifier: 'cryptocom',
    name: tc('import_data.cryptocom.name'),
    logo: './assets/images/crypto_com.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/CryptoComImport.vue')
    )
  },
  {
    identifier: 'blockfi',
    name: tc('import_data.blockfi.name'),
    logo: './assets/images/blockfi.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BlockFiImport.vue')
    )
  },
  {
    identifier: 'nexo',
    name: tc('import_data.nexo.name'),
    logo: './assets/images/nexo.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/NexoImport.vue')
    )
  },
  {
    identifier: 'shapeshift-trades',
    name: tc('import_data.shapeshift.name'),
    logo: './assets/images/shapeshift.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/ShapeshiftImport.vue')
    )
  },
  {
    identifier: 'uphold',
    name: tc('import_data.uphold.name'),
    logo: './assets/images/uphold.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/UpholdImport.vue')
    )
  },
  {
    identifier: 'bisq',
    name: tc('import_data.bisq.name'),
    logo: './assets/images/bisq.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BisqImport.vue')
    )
  },
  {
    identifier: 'binance',
    name: tc('import_data.binance.name'),
    logo: './assets/images/exchanges/binance.svg',
    form: defineAsyncComponent(
      () => import('@/components/import/BinanceImport.vue')
    )
  },
  {
    identifier: 'custom',
    name: tc('import_data.custom.name'),
    icon: 'mdi-book-open',
    form: defineAsyncComponent(
      () => import('@/components/import/CustomImport.vue')
    )
  }
];

const selectedSource = ref<string>('');

const form = computed(() => {
  return sources.find(source => source.identifier === get(selectedSource))
    ?.form;
});
</script>
<template>
  <card>
    <div class="pa-1 pt-2">
      <v-select
        v-model="selectedSource"
        :label="tc('import_data.select_source.title')"
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
