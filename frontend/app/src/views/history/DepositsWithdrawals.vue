<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('deposits_withdrawals.loading') }}
    </template>
    {{ $t('deposits_withdrawals.loading_subtitle') }}
  </progress-screen>
  <v-container v-else>
    <trade-location-selector
      v-model="location"
      :available-locations="availableLocations"
    />
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            {{ $t('deposits_withdrawals.title') }}
            <v-spacer />
            <refresh-button
              :loading="refreshing"
              :tooltip="$t('deposits_withdrawals.refresh_tooltip')"
              @refresh="fetchMovements(true)"
            />
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="movements"
              show-expand
              single-expand
              :expanded="expanded"
              item-key="identifier"
              sort-by="timestamp"
              sort-desc
              :page.sync="page"
              :footer-props="footerProps"
              :loading="refreshing"
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
                  assetMovementsLimit > 0
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
              <template #expanded-item="{ headers, item }">
                <td
                  :colspan="headers.length"
                  class="deposits-withdrawals__movement__details"
                >
                  <v-card outlined>
                    <v-card-title>
                      {{ $t('deposits_withdrawals.details.title') }}
                    </v-card-title>
                    <v-card-text>
                      <movement-links
                        v-if="item.address || item.transactionId"
                        :item="item"
                      />
                      <span v-else class="font-weight-medium">
                        {{ $t('deposits_withdrawals.details.no_details') }}
                      </span>
                    </v-card-text>
                  </v-card>
                </td>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins, Watch } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters } from 'vuex';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import MovementLinks from '@/components/history/MovementLinks.vue';
import TradeLocationSelector from '@/components/history/TradeLocationSelector.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { footerProps } from '@/config/datatable.common';
import StatusMixin from '@/mixins/status-mixin';
import { SupportedExchange } from '@/services/balances/types';
import { AssetMovement, TradeLocation } from '@/services/history/types';
import { Section } from '@/store/const';

@Component({
  components: {
    TradeLocationSelector,
    MovementLinks,
    RefreshButton,
    ProgressScreen,
    UpgradeRow,
    AssetDetails,
    LocationDisplay,
    DateDisplay
  },
  computed: {
    ...mapGetters('history', [
      'assetMovements',
      'assetMovementsTotal',
      'assetMovementsLimit'
    ])
  },
  methods: {
    ...mapActions('history', ['fetchMovements'])
  }
})
export default class DepositsWithdrawals extends Mixins(StatusMixin) {
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
    },
    { text: '', value: 'data-table-expand' }
  ];

  fetchMovements!: (refresh: boolean) => Promise<void>;
  assetMovements!: AssetMovement[];
  assetMovementsTotal!: number;
  assetMovementsLimit!: number;
  page: number = 1;

  location: SupportedExchange | null = null;

  @Watch('location')
  onLocationChange() {
    if (!location) {
      return;
    }
    this.page = 1;
  }

  get availableLocations(): TradeLocation[] {
    return this.assetMovements
      .map(movement => movement.location)
      .filter((value, index, array) => array.indexOf(value) === index);
  }

  get movements(): AssetMovement[] {
    return this.location
      ? this.assetMovements.filter(value => value.location === this.location)
      : this.assetMovements;
  }

  footerProps = footerProps;
  section = Section.ASSET_MOVEMENT;
  expanded = [];

  async mounted() {
    await this.fetchMovements(false);
  }
}
</script>

<style scoped lang="scss">
.deposits-withdrawals {
  &__movement {
    &__details {
      height: 150px !important;
      box-shadow: inset 1px 8px 10px -10px;
      background-color: var(--v-rotki-light-grey-base);
    }
  }
}
</style>
