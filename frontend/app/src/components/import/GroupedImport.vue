<template>
  <card>
    <div class="pa-2">
      <v-select
        v-model="selectedSource"
        :label="$t('import_data.select_source.title')"
        outlined
        :items="sources"
        item-value="identifier"
        item-text="name"
        :hide-details="true"
      >
        <template
          v-for="slotName in ['item', 'selection']"
          :slot="slotName"
          slot-scope="data"
        >
          <v-row v-if="data.item" :key="slotName">
            <v-col class="d-flex align-center justify-space-between col-12">
              <div
                :class="{
                  [$style.image]: true,
                  [$style['image--inverted']]: dark
                }"
              >
                <v-img
                  :src="data.item.logo"
                  max-height="100%"
                  max-width="100%"
                  position="center left"
                  :contain="true"
                />
              </div>
              <div v-if="slotName === 'item'">{{ data.item.name }}</div>
            </v-col>
          </v-row>
        </template>
      </v-select>

      <div v-if="form" class="mt-8">
        <component :is="form" />
      </div>
    </div>
  </card>
</template>
<script lang="ts">
import { computed, defineComponent, Ref, ref } from '@vue/composition-api';
import BisqImport from '@/components/import/Bisq.vue';
import BlockFiImport from '@/components/import/BlockFiImport.vue';
import CointrackingImport from '@/components/import/CointrackingImport.vue';
import CryptoComImport from '@/components/import/CryptoComImport.vue';
import GitcoinImport from '@/components/import/GitcoinImport.vue';
import NexoImport from '@/components/import/NexoImport.vue';
import ShapeshiftImport from '@/components/import/ShapeshiftImport.vue';
import UpholdImport from '@/components/import/UpholdImport.vue';
import { setupThemeCheck } from '@/composables/common';
import { getPremium } from '@/composables/session';
import i18n from '@/i18n';

const sources = (premium: Ref<boolean>) =>
  computed(() => {
    const sources = [
      {
        identifier: 'cointracking.info',
        name: i18n.t('import_data.cointracking.name').toString(),
        logo: require('@/assets/images/import/cointracking_info.svg'),
        form: 'cointracking-import'
      },
      {
        identifier: 'cryptocom',
        name: i18n.t('import_data.cryptocom.name').toString(),
        logo: require('@/assets/images/import/crypto_com.png'),
        form: 'crypto-com-import'
      },
      {
        identifier: 'blockfi',
        name: i18n.t('import_data.blockfi.name').toString(),
        logo: require('@/assets/images/import/blockfi.svg'),
        form: 'block-fi-import'
      },
      {
        identifier: 'nexo',
        name: i18n.t('import_data.nexo.name').toString(),
        logo: require('@/assets/images/import/nexo.svg'),
        form: 'nexo-import'
      },
      {
        identifier: 'shapeshift-trades',
        name: i18n.t('import_data.shapeshift.name').toString(),
        logo: require('@/assets/images/import/shape_shift.svg'),
        form: 'shapeshift-import'
      },
      {
        identifier: 'uphold',
        name: i18n.t('import_data.uphold.name').toString(),
        logo: require('@/assets/images/import/uphold.svg'),
        form: 'uphold-import'
      },
      {
        identifier: 'bisq',
        name: i18n.t('import_data.bisq.name'),
        logo: require('@/assets/images/bisq.svg'),
        form: 'bisq-import'
      }
    ];

    if (premium.value) {
      sources.push({
        identifier: 'gitcoin',
        name: i18n.t('import_data.gitcoin.name'),
        logo: require('@/assets/images/import/gitcoin.svg'),
        form: 'gitcoin-import'
      });
    }

    return sources;
  });

export default defineComponent({
  name: 'GroupedImport',
  components: {
    UpholdImport,
    ShapeshiftImport,
    NexoImport,
    BlockFiImport,
    CryptoComImport,
    CointrackingImport,
    BisqImport,
    GitcoinImport
  },
  setup() {
    const selectedSource = ref<string>('');
    const premium: Ref<boolean> = getPremium();

    const form = computed(() => {
      return sources(premium).value.find(
        source => source.identifier === selectedSource.value
      )?.form;
    });

    const { dark } = setupThemeCheck();

    return {
      selectedSource,
      form,
      dark,
      sources: sources(premium)
    };
  }
});
</script>
<style module lang="scss">
.image {
  max-width: 200px;
  height: 30px;
  max-height: 30px;

  > * {
    height: 30px;
  }

  &--inverted {
    filter: brightness(0) invert(100%);
  }
}
</style>
