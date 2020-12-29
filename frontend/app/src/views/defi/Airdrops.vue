<template>
  <v-container>
    <v-row>
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
    <v-container v-else>
      <blockchain-account-selector
        v-model="selectedAccounts"
        multiple
        class="mt-4"
        hint
        :chains="[ETH]"
        :usable-addresses="airdropAddresses"
      />
      <v-card class="mt-4">
        <v-card-text>
          <v-data-table
            :items="entries"
            :footer-props="footerProps"
            :headers="headers"
          >
            <template #item.address="{ item }">
              <hash-link :text="item.address" />
            </template>
            <template #item.amount="{ item }">
              <amount-display :value="item.amount" :asset="item.asset" />
            </template>
            <template #item.source="{ item }">
              <div class="d-flex flex-row align-center">
                <v-img
                  width="24px"
                  contain
                  position="left"
                  max-height="32px"
                  max-width="32px"
                  :src="getIcon(item.source)"
                />
                <span class="ms-2" v-text="getLabel(item.source)" />
              </div>
            </template>
          </v-data-table>
        </v-card-text>
      </v-card>
    </v-container>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { footerProps } from '@/config/datatable.common';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import {
  AIRDROP_1INCH,
  AIRDROP_TORNADO,
  AIRDROP_UNISWAP,
  AIRDROP_CORNICHON
} from '@/store/defi/const';
import { Airdrop, AirdropType } from '@/store/defi/types';
import { ETH, GeneralAccount } from '@/typing/types';

type AirdropSource = {
  readonly icon: string;
  readonly name: string;
};

type AirdropSources = {
  readonly [source in AirdropType]: AirdropSource;
};

@Component({
  components: { ProgressScreen },
  computed: {
    ...mapGetters('defi', ['airdrops', 'airdropAddresses'])
  },
  methods: {
    ...mapActions('defi', ['fetchAirdrops'])
  }
})
export default class Airdrops extends Mixins(StatusMixin) {
  readonly section = Section.DEFI_AIRDROPS;
  readonly ETH = ETH;
  readonly footerProps = footerProps;
  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('airdrops.headers.source').toString(),
      value: 'source'
    },
    {
      text: this.$t('airdrops.headers.address').toString(),
      value: 'address'
    },
    {
      text: this.$t('airdrops.headers.amount').toString(),
      value: 'amount',
      align: 'end'
    }
  ];
  airdrops!: (addresses: string[]) => Airdrop[];
  fetchAirdrops!: (refresh: boolean) => Promise<void>;
  selectedAccounts: GeneralAccount[] = [];
  airdropAddresses!: string[];

  async mounted() {
    await this.fetchAirdrops(false);
  }

  get entries(): Airdrop[] {
    const addresses = this.selectedAccounts.map(({ address }) => address);
    return this.airdrops(addresses);
  }

  async refresh() {
    await this.fetchAirdrops(true);
  }

  readonly sources: AirdropSources = {
    [AIRDROP_UNISWAP]: {
      icon: require(`@/assets/images/defi/uniswap.svg`),
      name: 'Uniswap'
    },
    [AIRDROP_1INCH]: {
      icon: require(`@/assets/images/1inch.svg`),
      name: '1inch'
    },
    [AIRDROP_TORNADO]: {
      icon: require(`@/assets/images/tornado.svg`),
      name: 'Tornado Cach'
    },
    [AIRDROP_CORNICHON]: {
      icon: require(`@/assets/images/cornichon.svg`),
      name: 'Cornichon'
    }
  };

  getIcon(source: AirdropType) {
    return this.sources[source].icon ?? '';
  }

  getLabel(source: AirdropType) {
    return this.sources[source].name ?? '';
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
