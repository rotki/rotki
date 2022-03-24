<template>
  <div>
    <v-row class="mt-8">
      <v-col>
        <refresh-header
          :loading="refreshing"
          :title="$t('airdrops.title')"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <progress-screen v-if="loading">
      <template #message>{{ $t('airdrops.loading') }}</template>
    </progress-screen>
    <div v-else>
      <blockchain-account-selector
        v-model="selectedAccounts"
        multiple
        class="mt-6"
        hint
        :chains="[ETH]"
        :usable-addresses="airdropAddresses"
      >
        <div class="text-caption mt-4" v-text="$t('airdrops.description')" />
      </blockchain-account-selector>
      <v-card class="mt-8">
        <v-card-text>
          <v-sheet outlined rounded>
            <data-table
              :items="entries"
              :headers="headers"
              single-expand
              :expanded.sync="expanded"
              item-key="index"
            >
              <template #item.address="{ item }">
                <hash-link :text="item.address" />
              </template>
              <template #item.amount="{ item }">
                <amount-display
                  v-if="!hasDetails(item.source)"
                  :value="item.amount"
                  :asset="item.asset"
                />
                <span v-else>{{ item.details.length }}</span>
              </template>
              <template #item.source="{ item }">
                <div class="d-flex flex-row align-center">
                  <adaptive-wrapper>
                    <v-img
                      width="24px"
                      contain
                      position="left"
                      max-height="32px"
                      max-width="32px"
                      :src="getIcon(item.source)"
                    />
                  </adaptive-wrapper>
                  <span class="ms-2" v-text="getLabel(item.source)" />
                </div>
              </template>
              <template #item.link="{ item }">
                <v-btn
                  v-if="!hasDetails(item.source)"
                  icon
                  color="primary"
                  :target="$interop.isPackaged ? undefined : '_blank'"
                  :href="$interop.isPackaged ? undefined : item.link"
                  @click="
                    $interop.isPackaged
                      ? $interop.navigate(item.link)
                      : undefined
                  "
                >
                  <v-icon>mdi-link</v-icon>
                </v-btn>
                <row-expander
                  v-else
                  :expanded="expanded.includes(item)"
                  @click="expanded = expanded.includes(item) ? [] : [item]"
                />
              </template>
              <template #expanded-item="{ headers, item }">
                <poap-delivery-airdrops
                  :items="item.details"
                  :colspan="headers.length"
                  :visible="hasDetails(item.source)"
                />
              </template>
            </data-table>
          </v-sheet>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Component, Mixins } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters } from 'vuex';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import DataTable from '@/components/helper/DataTable.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import StatusMixin from '@/mixins/status-mixin';
import ThemeMixin from '@/mixins/theme-mixin';
import { Section } from '@/store/const';
import {
  AIRDROP_1INCH,
  AIRDROP_CONVEX,
  AIRDROP_CORNICHON,
  AIRDROP_COW_GNOSIS,
  AIRDROP_COW_MAINNET,
  AIRDROP_CURVE,
  AIRDROP_ENS,
  AIRDROP_FOX,
  AIRDROP_FURUCOMBO,
  AIRDROP_GRAIN,
  AIRDROP_LIDO,
  AIRDROP_PARASWAP,
  AIRDROP_POAP,
  AIRDROP_SADDLE,
  AIRDROP_TORNADO,
  AIRDROP_UNISWAP
} from '@/store/defi/const';
import { Airdrop, AirdropType } from '@/store/defi/types';
import PoapDeliveryAirdrops from '@/views/defi/PoapDeliveryAirdrops.vue';

type AirdropSource = {
  readonly icon: string;
  readonly name: string;
};

type AirdropSources = {
  readonly [source in AirdropType]: AirdropSource;
};

@Component({
  components: {
    AdaptiveWrapper,
    DataTable,
    PoapDeliveryAirdrops,
    RowExpander,
    ProgressScreen
  },
  computed: {
    ...mapGetters('defi', ['airdrops', 'airdropAddresses'])
  },
  methods: {
    ...mapActions('defi', ['fetchAirdrops'])
  }
})
export default class Airdrops extends Mixins(StatusMixin, ThemeMixin) {
  readonly section = Section.DEFI_AIRDROPS;
  readonly ETH = Blockchain.ETH;
  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('airdrops.headers.source').toString(),
      value: 'source',
      width: '200px'
    },
    {
      text: this.$t('airdrops.headers.address').toString(),
      value: 'address'
    },
    {
      text: this.$t('airdrops.headers.amount').toString(),
      value: 'amount',
      align: 'end'
    },
    {
      text: '',
      value: 'link',
      align: 'end',
      width: '50px'
    }
  ];
  airdrops!: (addresses: string[]) => Airdrop[];
  fetchAirdrops!: (refresh: boolean) => Promise<void>;
  selectedAccounts: GeneralAccount[] = [];
  airdropAddresses!: string[];
  expanded = [];

  hasDetails(source: AirdropType): boolean {
    return [AIRDROP_POAP].includes(source);
  }

  async mounted() {
    await this.fetchAirdrops(false);
  }

  get entries(): Airdrop[] {
    const addresses = this.selectedAccounts.map(({ address }) => address);
    return this.airdrops(addresses).map((value, index) => ({
      ...value,
      index
    }));
  }

  async refresh() {
    await this.fetchAirdrops(true);
  }

  readonly sources: AirdropSources = {
    [AIRDROP_UNISWAP]: {
      icon: '/assets/images/defi/uniswap.svg',
      name: 'Uniswap'
    },
    [AIRDROP_1INCH]: {
      icon: '/assets/images/1inch.svg',
      name: '1inch'
    },
    [AIRDROP_TORNADO]: {
      icon: '/assets/images/airdrops/tornado.svg',
      name: 'Tornado Cash'
    },
    [AIRDROP_CORNICHON]: {
      icon: '/assets/images/airdrops/cornichon.svg',
      name: 'Cornichon'
    },
    [AIRDROP_GRAIN]: {
      icon: '/assets/images/airdrops/grain.png',
      name: 'Grain'
    },
    [AIRDROP_LIDO]: {
      icon: '/assets/images/airdrops/lido.svg',
      name: 'Lido'
    },
    [AIRDROP_FURUCOMBO]: {
      icon: '/assets/images/airdrops/furucombo.png',
      name: 'Furucombo'
    },
    [AIRDROP_CURVE]: {
      icon: '/assets/images/defi/curve.svg',
      name: 'Curve Finance'
    },
    [AIRDROP_POAP]: {
      icon: '/assets/images/airdrops/poap.svg',
      name: 'POAP Delivery'
    },
    [AIRDROP_CONVEX]: {
      icon: '/assets/images/airdrops/convex.jpeg',
      name: 'Convex'
    },
    [AIRDROP_FOX]: {
      icon: '/assets/images/shapeshift.svg',
      name: 'ShapeShift'
    },
    [AIRDROP_ENS]: {
      icon: '/assets/images/airdrops/ens.svg',
      name: 'ENS'
    },
    [AIRDROP_PARASWAP]: {
      icon: '/assets/images/airdrops/paraswap.svg',
      name: 'ParaSwap'
    },
    [AIRDROP_SADDLE]: {
      icon: '/assets/images/airdrops/saddle-finance.svg',
      name: 'SaddleFinance'
    },
    [AIRDROP_COW_MAINNET]: {
      icon: '/assets/images/airdrops/cow.svg',
      name: 'COW (ethereum)'
    },
    [AIRDROP_COW_GNOSIS]: {
      icon: '/assets/images/airdrops/cow.svg',
      name: 'COW (gnosis chain)'
    }
  };

  getIcon(source: AirdropType) {
    return this.sources[source]?.icon ?? '';
  }

  getLabel(source: AirdropType) {
    return this.sources[source]?.name ?? '';
  }
}
</script>

<style scoped lang="scss">
::v-deep {
  tbody {
    tr {
      height: 72px;
    }
  }
}
</style>
