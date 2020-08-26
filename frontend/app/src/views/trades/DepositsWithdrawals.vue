<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            {{ $t('deposits_withdrawals.title') }}
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="assetMovements"
              item-key="identifier"
              sort-by="timestamp"
              sort-desc
              :footer-props="{
                showFirstLastPage: true,
                firstIcon: 'mdi-chevron-double-left',
                lastIcon: 'mdi-chevron-double-right',
                prevIcon: 'mdi-chevron-left',
                nextIcon: 'mdi-chevron-right',
                'items-per-page-options': [10, 25, 50, 100]
              }"
            >
              <template #item.location="{ item }">
                <location-display :identifier="item.location" />
              </template>
              <template #item.asset="{ item }">
                <asset-details :asset="item.asset" />
              </template>
              <template #item.amount="{ item }">
                <amount-display
                  class="deposits-withdrawals__movement__amount"
                  :value="item.amount"
                />
              </template>
              <template #item.fee="{ item }">
                <amount-display
                  class="closed-trades__trade__fee"
                  :asset="item.feeAsset"
                  :value="item.fee"
                />
              </template>
              <template #item.timestamp="{ item }">
                <date-display :timestamp="item.timestamp" />
              </template>
              <template
                v-if="
                  assetMovementsLimit <= assetMovementsTotal &&
                  assetMovementsTotal !== 0
                "
                #body.append="{ headers }"
              >
                <upgrade-row
                  :total="assetMovementsTotal"
                  :limit="assetMovementsLimit"
                  :colspan="headers.length"
                  :label="$t('deposits_withdrawals.label')"
                />
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters } from 'vuex';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import LocationDisplay from '@/components/trades/LocationDisplay.vue';
import { AssetMovement } from '@/services/balances/types';
import UpgradeRow from '@/views/trades/UpgradeRow.vue';

@Component({
  components: {
    UpgradeRow,
    AssetDetails,
    LocationDisplay,
    DateDisplay
  },
  computed: {
    ...mapGetters('balances', [
      'assetMovements',
      'assetMovementsTotal',
      'assetMovementsLimit'
    ])
  },
  methods: {
    ...mapActions('balances', ['fetchMovements'])
  }
})
export default class DepositsWithdrawals extends Vue {
  readonly headers: DataTableHeader[] = [
    {
      text: this.$tc('deposits_withdrawals.headers.location'),
      value: 'location'
    },
    {
      text: this.$tc('deposits_withdrawals.headers.action'),
      value: 'category'
    },
    {
      text: this.$tc('deposits_withdrawals.headers.asset'),
      value: 'asset'
    },
    {
      text: this.$tc('deposits_withdrawals.headers.amount'),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$tc('deposits_withdrawals.headers.fee'),
      value: 'fee',
      align: 'end'
    },
    {
      text: this.$tc('deposits_withdrawals.headers.timestamp'),
      value: 'timestamp'
    }
  ];

  fetchMovements!: () => Promise<void>;
  assetMovements!: AssetMovement[];
  assetMovementsTotal!: number;
  assetMovementsLimit!: number;

  async mounted() {
    await this.fetchMovements();
  }
}
</script>
