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
    <v-card class="mt-8">
      <v-card-title>
        <refresh-button
          :loading="refreshing"
          :tooltip="$t('deposits_withdrawals.refresh_tooltip')"
          @refresh="refresh"
        />
        <card-title class="ms-2">
          {{ $t('deposits_withdrawals.title') }}
        </card-title>
      </v-card-title>
      <v-card-text>
        <ignore-buttons
          :disabled="selected.length === 0 || loading || refreshing"
          @ignore="ignoreMovements"
        />
        <v-sheet outlined rounded>
          <data-table
            :headers="headers"
            :items="movements"
            show-expand
            single-expand
            :expanded="expanded"
            item-key="identifier"
            sort-by="timestamp"
            :page.sync="page"
            :loading="refreshing"
          >
            <template #header.selection>
              <v-simple-checkbox
                :ripple="false"
                :value="allSelected"
                color="primary"
                @input="setSelected($event)"
              />
            </template>
            <template #item.selection="{ item }">
              <v-simple-checkbox
                :ripple="false"
                color="primary"
                :value="selected.includes(item.identifier)"
                @input="selectionChanged(item.identifier, $event)"
              />
            </template>
            <template #item.ignoredInAccounting="{ item }">
              <v-icon v-if="item.ignoredInAccounting">mdi-check</v-icon>
            </template>
            <template #item.location="{ item }">
              <location-display :identifier="item.location" />
            </template>
            <template #item.asset="{ item }">
              <asset-details opens-details :asset="item.asset" />
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
              <table-expand-container visible :colspan="headers.length">
                <template #title>
                  {{ $t('deposits_withdrawals.details.title') }}
                </template>
                <movement-links
                  v-if="item.address || item.transactionId"
                  :item="item"
                />
                <div
                  v-else
                  class="font-weight-medium pa-4 deposits-withdrawals__movement__details--empty"
                >
                  {{ $t('deposits_withdrawals.details.no_details') }}
                </div>
              </table-expand-container>
            </template>
          </data-table>
        </v-sheet>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script lang="ts">
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import { Component, Mixins, Watch } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters, mapMutations } from 'vuex';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import DataTable from '@/components/helper/DataTable.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import MovementLinks from '@/components/history/MovementLinks.vue';
import TradeLocationSelector from '@/components/history/TradeLocationSelector.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import StatusMixin from '@/mixins/status-mixin';
import { SupportedExchange } from '@/services/balances/types';
import { TradeLocation } from '@/services/history/types';
import { Section } from '@/store/const';
import {
  FETCH_FROM_CACHE,
  FETCH_FROM_SOURCE,
  FETCH_REFRESH,
  HistoryActions,
  IGNORE_MOVEMENTS
} from '@/store/history/consts';
import {
  AssetMovementEntry,
  FetchSource,
  IgnoreActionPayload
} from '@/store/history/types';
import { ActionStatus, Message } from '@/store/types';

@Component({
  components: {
    TableExpandContainer,
    DataTable,
    CardTitle,
    IgnoreButtons,
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
    ...mapActions('history', [
      HistoryActions.FETCH_MOVEMENTS,
      HistoryActions.IGNORE_ACTIONS,
      HistoryActions.UNIGNORE_ACTION
    ]),
    ...mapMutations(['setMessage'])
  }
})
export default class DepositsWithdrawals extends Mixins(StatusMixin) {
  readonly headers: DataTableHeader[] = [
    { text: '', value: 'selection', width: '34px', sortable: false },
    {
      text: this.$tc('deposits_withdrawals.headers.location'),
      value: 'location',
      width: '120px',
      align: 'center'
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
    {
      text: this.$t('deposits_withdrawals.headers.ignored').toString(),
      value: 'ignoredInAccounting'
    },
    { text: '', value: 'data-table-expand' }
  ];

  fetchMovements!: (payload: FetchSource) => Promise<void>;
  ignoreActions!: (actionsIds: IgnoreActionPayload) => Promise<ActionStatus>;
  unignoreActions!: (actionsIds: IgnoreActionPayload) => Promise<ActionStatus>;
  setMessage!: (message: Message) => void;
  assetMovements!: AssetMovementEntry[];
  assetMovementsTotal!: number;
  assetMovementsLimit!: number;
  page: number = 1;

  location: SupportedExchange | null = null;
  selected: string[] = [];

  setSelected(selected: boolean) {
    const selection = this.selected;
    if (!selected) {
      const total = selection.length;
      for (let i = 0; i < total; i++) {
        selection.pop();
      }
    } else {
      for (const { identifier } of this.movements) {
        if (!identifier || selection.includes(identifier)) {
          continue;
        }
        selection.push(identifier);
      }
    }
  }

  selectionChanged(identifier: string, selected: boolean) {
    const selection = this.selected;
    if (!selected) {
      const index = selection.indexOf(identifier);
      if (index >= 0) {
        selection.splice(index, 1);
      }
    } else if (identifier && !selection.includes(identifier)) {
      selection.push(identifier);
    }
  }

  get allSelected(): boolean {
    const strings = this.movements.map(({ identifier }) => identifier);
    return (
      strings.length > 0 && isEqual(sortBy(strings), sortBy(this.selected))
    );
  }

  async ignoreMovements(ignore: boolean) {
    let status: ActionStatus;

    const actionIds = this.movements
      .filter(({ identifier, ignoredInAccounting }) => {
        return (
          (ignore ? !ignoredInAccounting : ignoredInAccounting) &&
          this.selected.includes(identifier)
        );
      })
      .map(({ identifier }) => identifier)
      .filter((value, index, array) => array.indexOf(value) === index);

    if (actionIds.length === 0) {
      const choice = ignore ? 1 : 2;
      this.setMessage({
        success: false,
        title: this.$tc('deposits_withdrawals.ignore.no_actions.title', choice),
        description: this.$tc(
          'deposits_withdrawals.ignore.no_actions.description',
          choice
        )
      });
      return;
    }
    const payload: IgnoreActionPayload = {
      actionIds: actionIds,
      type: IGNORE_MOVEMENTS
    };
    if (ignore) {
      status = await this.ignoreActions(payload);
    } else {
      status = await this.unignoreActions(payload);
    }

    if (status.success) {
      const total = this.selected.length;
      for (let i = 0; i < total; i++) {
        this.selected.pop();
      }
    }
  }

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

  get movements(): AssetMovementEntry[] {
    return this.location
      ? this.assetMovements.filter(value => value.location === this.location)
      : this.assetMovements;
  }

  section = Section.ASSET_MOVEMENT;
  expanded = [];

  async mounted() {
    await this.fetchMovements(FETCH_FROM_CACHE);
    await this.fetchMovements(FETCH_FROM_SOURCE);
  }

  async refresh() {
    await this.fetchMovements(FETCH_REFRESH);
  }
}
</script>

<style scoped lang="scss">
.deposits-withdrawals {
  &__movement {
    &__details {
      &--empty {
        height: 100px;
      }
    }
  }
}

::v-deep {
  th {
    &:nth-child(2) {
      span {
        padding-left: 16px;
      }
    }
  }
}
</style>
