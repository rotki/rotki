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
                :src="data.item.logo"
                :width="30"
                :height="30"
                max-height="30px"
                max-width="30px"
                position="center left"
                contain
              />
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
<script setup lang="ts">
import { get } from '@vueuse/core';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';

const { tc } = useI18n();
const sources = [
  {
    identifier: 'cointracking.info',
    name: tc('import_data.cointracking.name'),
    logo: '/assets/images/cointracking.svg',
    form: 'cointracking-import'
  },
  {
    identifier: 'cryptocom',
    name: tc('import_data.cryptocom.name'),
    logo: '/assets/images/crypto_com.svg',
    form: 'crypto-com-import'
  },
  {
    identifier: 'blockfi',
    name: tc('import_data.blockfi.name'),
    logo: '/assets/images/blockfi.svg',
    form: 'block-fi-import'
  },
  {
    identifier: 'nexo',
    name: tc('import_data.nexo.name'),
    logo: '/assets/images/nexo.svg',
    form: 'nexo-import'
  },
  {
    identifier: 'shapeshift-trades',
    name: tc('import_data.shapeshift.name'),
    logo: '/assets/images/shapeshift.svg',
    form: 'shapeshift-import'
  },
  {
    identifier: 'uphold',
    name: tc('import_data.uphold.name'),
    logo: '/assets/images/uphold.svg',
    form: 'uphold-import'
  },
  {
    identifier: 'bisq',
    name: tc('import_data.bisq.name'),
    logo: '/assets/images/bisq.svg',
    form: 'bisq-import'
  },
  {
    identifier: 'binance',
    name: tc('import_data.binance.name'),
    logo: '/assets/images/exchanges/binance.svg',
    form: 'binance-import'
  }
];

const selectedSource = ref<string>('');

const form = computed(() => {
  return sources.find(source => source.identifier === get(selectedSource))
    ?.form;
});
</script>
