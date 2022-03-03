<template>
  <v-container class="pb-12">
    <v-row align="center" class="mt-12">
      <v-col cols="auto">
        <asset-icon :identifier="identifier" size="48px" />
      </v-col>
      <v-col class="d-flex flex-column" cols="auto">
        <span class="text-h5 font-weight-medium">{{ symbol }}</span>
        <span class="text-subtitle-2 text--secondary">
          {{ assetName }}
        </span>
      </v-col>
      <v-col cols="auto">
        <v-btn icon :to="editRoute">
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <asset-value-row class="mt-8" :identifier="identifier" :symbol="symbol" />
    <asset-amount-and-value-over-time
      v-if="premium"
      class="mt-8"
      :service="$api"
      :asset="identifier"
    />
    <asset-locations class="mt-8" :identifier="identifier" />
  </v-container>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { RawLocation } from 'vue-router/types/router';
import AssetLocations from '@/components/assets/AssetLocations.vue';
import AssetValueRow from '@/components/assets/AssetValueRow.vue';
import { setupAssetInfoRetrieval } from '@/composables/balances';
import { getPremium } from '@/composables/session';
import { AssetAmountAndValueOverTime } from '@/premium/premium';
import { Routes } from '@/router/routes';

export default defineComponent({
  name: 'Assets',
  components: { AssetLocations, AssetValueRow, AssetAmountAndValueOverTime },
  props: {
    identifier: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const editRoute = computed<RawLocation>(() => {
      return {
        path: Routes.ASSET_MANAGER,
        query: {
          id: get(identifier)
        }
      };
    });

    const premium = getPremium();

    const { getAssetName, getAssetSymbol } = setupAssetInfoRetrieval();

    const assetName = computed<string>(() => {
      return getAssetName(get(identifier));
    });

    const symbol = computed<string>(() => {
      return getAssetSymbol(get(identifier));
    });

    return {
      premium,
      editRoute,
      assetName,
      symbol
    };
  }
});
</script>
