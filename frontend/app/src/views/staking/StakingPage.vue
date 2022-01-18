<template>
  <v-container>
    <card>
      <div class="pa-2">
        <v-select
          :value="location"
          outlined
          hide-details
          :items="staking"
          item-value="id"
          @change="updateLocation"
        >
          <template
            v-for="slot in ['item', 'selection']"
            :slot="slot"
            slot-scope="data"
          >
            <v-row v-if="data.item" :key="slot">
              <v-col class="d-flex align-center justify-space-between col-12">
                <div>
                  <v-img
                    v-if="data.item.img"
                    width="22px"
                    contain
                    max-height="24px"
                    :src="data.item.icon"
                  />
                  <asset-icon
                    v-else
                    size="24px"
                    :identifier="getAssetIdentifierForSymbol(data.item.icon)"
                  />
                </div>
                <div v-if="slot === 'item'">{{ data.item.name }}</div>
              </v-col>
            </v-row>
          </template>
        </v-select>
      </div>
    </card>
    <component :is="page" v-if="page" class="pt-4" />
    <full-size-content v-else>
      <v-row align="center" justify="center">
        <v-col>
          <span class="font-weight-light text-h6">
            {{ $t('staking_page.hint') }}
          </span>
        </v-col>
      </v-row>
    </full-size-content>
  </v-container>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import { setupAssetInfoRetrieval } from '@/composables/balances';
import { setupThemeCheck, useRouter } from '@/composables/common';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import AdexPage from '@/views/staking/AdexPage.vue';
import Eth2Page from '@/views/staking/Eth2Page.vue';
import KrakenPage from '@/views/staking/KrakenPage.vue';
import LiquityPage from '@/views/staking/LiquityPage.vue';

type StakinInfo = {
  id: string;
  icon: string;
  name: string;
  img?: boolean;
};

const staking: StakinInfo[] = [
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
    icon: require('@/assets/images/kraken.png'),
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
  components: { FullSizeContent },
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
    const { getAssetIdentifierForSymbol } = setupAssetInfoRetrieval();

    const page = computed(() => {
      const selectedLocation = location.value;
      return selectedLocation ? pages[selectedLocation] : null;
    });

    const router = useRouter();

    const updateLocation = (location: string) => {
      router.push(Routes.STAKING.replace(':location*', location));
    };

    return {
      dark,
      staking,
      pages,
      page,
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
</style>
