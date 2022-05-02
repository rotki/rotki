<template>
  <v-container class="pb-12">
    <v-row class="mt-12" align="center" justify="space-between">
      <v-col>
        <v-row align="center">
          <v-col cols="auto">
            <asset-icon :identifier="identifier" size="48px" />
          </v-col>
          <v-col class="d-flex flex-column" cols="auto">
            <span class="text-h5 font-weight-medium">{{ symbol }}</span>
            <span class="text-subtitle-2 text--secondary">
              {{ name }}
            </span>
          </v-col>
          <v-col cols="auto">
            <v-btn icon :to="editRoute">
              <v-icon>mdi-pencil</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="auto">
        <v-row align="center">
          <v-col cols="auto">
            <div class="text-subtitle-2">{{ $t('assets.ignore') }}</div>
          </v-col>
          <v-col>
            <v-switch
              :input-value="isAssetIgnored"
              @change="toggleIgnoreAsset"
            />
          </v-col>
        </v-row>
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
import { getPremium, setupIgnoredAssets } from '@/composables/session';
import { AssetAmountAndValueOverTime } from '@/premium/premium';
import { Routes } from '@/router/routes';
import { useAssetInfoRetrieval } from '@/store/assets';

export default defineComponent({
  name: 'Assets',
  components: { AssetLocations, AssetValueRow, AssetAmountAndValueOverTime },
  props: {
    identifier: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);
    const { ignoredAssets, ignoreAsset, unignoreAsset } = setupIgnoredAssets();

    const findIgnoredAssetIndex = () => {
      return get(ignoredAssets).indexOf(get(identifier));
    };

    const isAssetIgnored = computed<boolean>(() => {
      return findIgnoredAssetIndex() > -1;
    });

    const toggleIgnoreAsset = () => {
      if (findIgnoredAssetIndex() > -1) {
        unignoreAsset(get(identifier));
      } else {
        ignoreAsset(get(identifier));
      }
    };

    const editRoute = computed<RawLocation>(() => {
      return {
        path: Routes.ASSET_MANAGER,
        query: {
          id: get(identifier)
        }
      };
    });

    const premium = getPremium();

    const { assetName, assetSymbol } = useAssetInfoRetrieval();

    const name = computed<string>(() => {
      return get(assetName(get(identifier)));
    });

    const symbol = computed<string>(() => {
      return get(assetSymbol(get(identifier)));
    });

    return {
      isAssetIgnored,
      toggleIgnoreAsset,
      premium,
      editRoute,
      name,
      symbol
    };
  }
});
</script>
