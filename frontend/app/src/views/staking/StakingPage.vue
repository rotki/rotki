<template>
  <v-container>
    <card>
      <div class="pa-2">
        <v-select
          :value="location"
          outlined
          hide-details
          :items="staking"
          :label="$t('staking_page.dropdown_label')"
          item-value="id"
          @change="updateLocation"
        >
          <template
            v-for="slot in ['item', 'selection']"
            :slot="slot"
            slot-scope="data"
          >
            <v-row v-if="data.item" :key="slot" align="center">
              <v-col cols="auto">
                <adaptive-wrapper v-if="data.item.img" width="24" height="24">
                  <v-img
                    width="24px"
                    contain
                    max-height="24px"
                    :src="data.item.icon"
                  />
                </adaptive-wrapper>

                <asset-icon
                  v-else
                  size="24px"
                  :identifier="getAssetIdentifierForSymbol(data.item.icon)"
                />
              </v-col>
              <v-col class="pl-0">
                {{ data.item.name }}
              </v-col>
            </v-row>
          </template>
        </v-select>
      </div>
    </card>
    <div v-if="page" class="pt-4">
      <component :is="page" />
    </div>
    <div v-else>
      <div
        class="d-flex flex-row align-center justify-md-end justify-center mt-2 mr-md-6"
      >
        <div class="flex-shrink-0">
          <v-icon>mdi-arrow-up-left</v-icon>
        </div>
        <div class="text--secondary pt-3 flex-shrink-0 ms-2">
          {{ $t('staking_page.dropdown_hint') }}
        </div>
      </div>
      <full-size-content>
        <v-row align="center" justify="center">
          <v-col>
            <v-row align="center" justify="center">
              <v-col cols="auto">
                <span class="font-weight-bold text-h5">
                  {{ $t('staking_page.page.title') }}
                </span>
              </v-col>
            </v-row>
            <v-row justify="center" class="mt-md-12 mt-4">
              <v-col cols="auto" class="mx-4">
                <router-link to="/staking/eth2">
                  <asset-icon
                    no-tooltip
                    :identifier="getAssetIdentifierForSymbol('ETH')"
                    :size="iconSize"
                  />
                </router-link>
              </v-col>
              <v-col cols="auto" class="mx-4">
                <router-link to="/staking/adex">
                  <asset-icon
                    no-tooltip
                    :identifier="getAssetIdentifierForSymbol('ADX')"
                    :size="iconSize"
                  />
                </router-link>
              </v-col>
              <v-col cols="auto" class="mx-4">
                <router-link to="/staking/liquity">
                  <asset-icon
                    no-tooltip
                    :identifier="getAssetIdentifierForSymbol('LQTY')"
                    :size="iconSize"
                  />
                </router-link>
              </v-col>
              <v-col cols="auto" class="mx-4">
                <router-link to="/staking/kraken">
                  <v-img
                    :width="iconSize"
                    contain
                    src="/assets/images/exchanges/kraken.svg"
                  />
                </router-link>
              </v-col>
            </v-row>

            <v-row class="mt-md-10 mt-2" justify="center">
              <v-col cols="auto">
                <div
                  class="font-weight-light text-h6"
                  :class="$style.description"
                >
                  {{ $t('staking_page.page.description') }}
                </div>
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </full-size-content>
    </div>
  </v-container>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onBeforeMount,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get, set, useLocalStorage } from '@vueuse/core';
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { setupThemeCheck, useRouter } from '@/composables/common';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { useAssetInfoRetrieval } from '@/store/assets';
import AdexPage from '@/views/staking/AdexPage.vue';
import Eth2Page from '@/views/staking/Eth2Page.vue';
import KrakenPage from '@/views/staking/KrakenPage.vue';
import LiquityPage from '@/views/staking/LiquityPage.vue';

type StakingInfo = {
  id: string;
  icon: string;
  name: string;
  img?: boolean;
};

const staking: StakingInfo[] = [
  {
    id: 'eth2',
    icon: 'ETH',
    name: i18n.t('staking.eth2').toString()
  },
  {
    id: 'adex',
    icon: 'ADX',
    name: i18n.t('staking.adex').toString()
  },
  {
    id: 'liquity',
    icon: 'LQTY',
    name: i18n.t('staking.liquity').toString()
  },
  {
    id: 'kraken',
    icon: '/assets/images/exchanges/kraken.svg',
    name: i18n.t('staking.kraken').toString(),
    img: true
  }
];

const pages = {
  eth2: Eth2Page,
  adex: AdexPage,
  liquity: LiquityPage,
  kraken: KrakenPage
};

export default defineComponent({
  name: 'StakingPage',
  components: { AdaptiveWrapper, FullSizeContent },
  props: {
    location: {
      required: false,
      type: String as PropType<'eth2' | 'adex' | 'liquity' | 'kraken' | null>,
      default: null
    }
  },
  setup(props) {
    const { location } = toRefs(props);
    const { dark } = setupThemeCheck();
    const { getAssetIdentifierForSymbol } = useAssetInfoRetrieval();

    const lastLocation = useLocalStorage('rotki.staking.last_location', '');

    const page = computed(() => {
      const selectedLocation = get(location);
      return selectedLocation ? pages[selectedLocation] : null;
    });

    const router = useRouter();

    const updateLocation = (location: string) => {
      if (location) {
        set(lastLocation, location);
      }
      router.push(Routes.STAKING.route.replace(':location*', location));
    };

    onBeforeMount(() => {
      if (get(lastLocation)) {
        updateLocation(get(lastLocation));
      }
    });

    return {
      dark,
      staking,
      pages,
      page,
      iconSize: '64px',
      getAssetIdentifierForSymbol,
      updateLocation
    };
  }
});
</script>

<style lang="scss" module>
.content {
  height: calc(100% - 120px);
}

.description {
  text-align: center;
  max-width: 600px;
}
</style>
