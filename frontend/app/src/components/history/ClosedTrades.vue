<template>
  <fragment>
    <v-card class="mt-8">
      <v-btn
        absolute
        fab
        top
        right
        dark
        color="primary"
        class="closed-trades__add-trade"
        @click="newExternalTrade()"
      >
        <v-icon> mdi-plus </v-icon>
      </v-btn>
      <v-card-title>
        <refresh-button
          :loading="refreshing"
          :tooltip="$t('closed_trades.refresh_tooltip')"
          @refresh="refresh"
        />

        <card-title class="ms-2">{{ $t('closed_trades.title') }}</card-title>
      </v-card-title>
      <v-card-text>
        <ignore-buttons
          :disabled="selected.length === 0 || loading || refreshing"
          @ignore="ignoreTrades"
        />
        <v-sheet outlined rounded>
          <data-table
            :items="data"
            :headers="headersClosed"
            :expanded.sync="expanded"
            single-expand
            show-expand
            sort-by="timestamp"
            class="closed-trades"
            item-key="tradeId"
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
            <template #item.baseAsset="{ item }">
              <asset-details
                v-if="typeof item.baseAsset === 'string'"
                data-cy="trade_base"
                hide-name
                :asset="item.baseAsset"
              />
              <asset-details-base
                v-else
                data-cy="trade_base"
                hide-name
                :asset="item.baseAsset"
              />
            </template>
            <template #item.quoteAsset="{ item }">
              <asset-details
                v-if="typeof item.quoteAsset === 'string'"
                data-cy="trade_quote"
                hide-name
                :asset="item.quoteAsset"
              />
              <asset-details-base
                v-else
                hide-name
                :asset="item.quoteAsset"
                data-cy="trade_quote"
              />
            </template>
            <template #item.description="{ item }">
              {{
                item.tradeType === 'buy'
                  ? $t('closed_trades.description.with')
                  : $t('closed_trades.description.for')
              }}
            </template>
            <template #item.selection="{ item }">
              <v-simple-checkbox
                :ripple="false"
                color="primary"
                :value="selected.includes(item.tradeId)"
                @input="selectionChanged(item.tradeId, $event)"
              />
            </template>
            <template #item.location="{ item }">
              <location-display :identifier="item.location" />
            </template>
            <template #item.rate="{ item }">
              <amount-display
                class="closed-trades__trade__rate"
                :value="item.rate"
              />
            </template>
            <template #item.amount="{ item }">
              <amount-display
                class="closed-trades__trade__amount"
                :value="item.amount"
              />
            </template>
            <template #item.ignoredInAccounting="{ item }">
              <v-icon v-if="item.ignoredInAccounting">mdi-check</v-icon>
            </template>
            <template #item.timestamp="{ item }">
              <div class="d-flex flex-row align-center">
                <date-display :timestamp="item.timestamp" />
                <v-spacer v-if="item.location === 'external'" />
                <div v-if="item.location === 'external'">
                  <v-btn icon>
                    <v-icon
                      small
                      class="closed-trades__trade__actions__edit"
                      @click="editTrade(item)"
                    >
                      mdi-pencil
                    </v-icon>
                  </v-btn>
                  <v-btn icon>
                    <v-icon
                      class="closed-trades__trade__actions__delete"
                      small
                      @click="promptForDelete(item)"
                    >
                      mdi-delete
                    </v-icon>
                  </v-btn>
                </div>
              </div>
            </template>

            <template #expanded-item="{ headers, item }">
              <table-expand-container visible :colspan="headers.length">
                <template #title>
                  {{ $t('closed_trades.details.title') }}
                </template>
                <v-row>
                  <v-col cols="auto" class="font-weight-medium">
                    {{ $t('closed_trades.details.fee') }}
                  </v-col>
                  <v-col>
                    <amount-display
                      v-if="!!item.fee"
                      class="closed-trades__trade__fee"
                      :asset="item.feeCurrency"
                      :value="item.fee"
                    />
                    <span v-else>-</span>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col cols="auto" class="font-weight-medium">
                    {{ $t('closed_trades.details.link') }}
                  </v-col>
                  <v-col>
                    {{
                      item.link
                        ? item.link
                        : $t('closed_trades.details.link_data')
                    }}
                  </v-col>
                </v-row>
                <notes-display :notes="item.notes" />
              </table-expand-container>
            </template>
            <template
              v-if="tradesLimit <= tradesTotal && tradesLimit > 0"
              #body.append="{ headers }"
            >
              <upgrade-row
                :limit="tradesLimit"
                :total="tradesTotal"
                :colspan="headers.length"
                :label="$t('closed_trades.label')"
              />
            </template>
          </data-table>
        </v-sheet>
      </v-card-text>
    </v-card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :primary-action="$t('closed_trades.dialog.save')"
      :action-disabled="loading || !valid"
      :loading="loading"
      @confirm="save()"
      @cancel="clearDialog()"
    >
      <external-trade-form ref="form" v-model="valid" :edit="editableItem" />
    </big-dialog>
    <confirm-dialog
      :display="tradeToDelete !== null"
      :title="$t('closed_trades.confirmation.title')"
      confirm-type="warning"
      :message="confirmationMessage"
      @cancel="tradeToDelete = null"
      @confirm="deleteTrade()"
    />
  </fragment>
</template>

<script lang="ts">
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import { Component, Emit, Mixins, Prop, Watch } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters, mapMutations } from 'vuex';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import ExternalTradeForm from '@/components/ExternalTradeForm.vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import DataTable from '@/components/helper/DataTable.vue';
import Fragment from '@/components/helper/Fragment';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import NotesDisplay from '@/components/helper/table/NotesDisplay.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import AssetMixin from '@/mixins/asset-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import { HistoryActions, IGNORE_TRADES } from '@/store/history/consts';
import { IgnoreActionPayload, TradeEntry } from '@/store/history/types';
import { ActionStatus, Message } from '@/store/types';

@Component({
  components: {
    NotesDisplay,
    AssetDetailsBase,
    DataTable,
    TableExpandContainer,
    Fragment,
    CardTitle,
    IgnoreButtons,
    RefreshButton,
    UpgradeRow,
    DateDisplay,
    LocationDisplay,
    ExternalTradeForm,
    ConfirmDialog,
    BigDialog
  },
  computed: {
    ...mapGetters('history', ['tradesTotal', 'tradesLimit'])
  },
  methods: {
    ...mapActions('history', [
      HistoryActions.DELETE_EXTERNAL_TRADE,
      HistoryActions.IGNORE_ACTIONS,
      HistoryActions.UNIGNORE_ACTION
    ]),
    ...mapMutations(['setMessage'])
  }
})
export default class ClosedTrades extends Mixins(StatusMixin, AssetMixin) {
  readonly headersClosed: DataTableHeader[] = [
    { text: '', value: 'selection', width: '34px', sortable: false },
    {
      text: this.$tc('closed_trades.headers.location'),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: this.$tc('closed_trades.headers.action'),
      value: 'tradeType',
      width: '90px'
    },
    {
      text: this.$t('closed_trades.headers.base').toString(),
      value: 'baseAsset'
    },
    {
      text: '',
      value: 'description',
      sortable: false,
      width: '40px'
    },
    {
      text: this.$t('closed_trades.headers.quote').toString(),
      value: 'quoteAsset'
    },
    {
      text: this.$tc('closed_trades.headers.rate'),
      value: 'rate',
      align: 'end'
    },
    {
      text: this.$tc('closed_trades.headers.amount'),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$tc('closed_trades.headers.timestamp'),
      value: 'timestamp'
    },
    {
      text: this.$t('closed_trades.headers.ignored').toString(),
      value: 'ignoredInAccounting'
    },
    { text: '', value: 'data-table-expand' }
  ];

  dialogTitle: string = '';
  dialogSubtitle: string = '';
  openDialog: boolean = false;
  editableItem: TradeEntry | null = null;
  tradeToDelete: TradeEntry | null = null;
  confirmationMessage: string = '';
  tradesLimit!: number;
  tradesTotal!: number;
  expanded = [];
  page: number = 1;
  valid: boolean = false;

  deleteExternalTrade!: (tradeId: string) => Promise<boolean>;
  ignoreActions!: (actionsIds: IgnoreActionPayload) => Promise<ActionStatus>;
  unignoreActions!: (actionsIds: IgnoreActionPayload) => Promise<ActionStatus>;
  setMessage!: (message: Message) => void;
  section = Section.TRADES;

  selected: string[] = [];

  setSelected(selected: boolean) {
    const selection = this.selected;
    if (!selected) {
      const total = selection.length;
      for (let i = 0; i < total; i++) {
        selection.pop();
      }
    } else {
      for (const { tradeId } of this.data) {
        if (!tradeId || selection.includes(tradeId)) {
          continue;
        }
        selection.push(tradeId);
      }
    }
  }

  selectionChanged(tradeId: string, selected: boolean) {
    const selection = this.selected;
    if (!selected) {
      const index = selection.indexOf(tradeId);
      if (index >= 0) {
        selection.splice(index, 1);
      }
    } else if (tradeId && !selection.includes(tradeId)) {
      selection.push(tradeId);
    }
  }

  get allSelected(): boolean {
    const strings = this.data.map(({ tradeId }) => tradeId);
    return (
      strings.length > 0 && isEqual(sortBy(strings), sortBy(this.selected))
    );
  }

  async ignoreTrades(ignore: boolean) {
    let status: ActionStatus;

    const actionIds = this.data
      .filter(({ tradeId, ignoredInAccounting }) => {
        return (
          (ignore ? !ignoredInAccounting : ignoredInAccounting) &&
          this.selected.includes(tradeId)
        );
      })
      .map(({ tradeId }) => tradeId)
      .filter((value, index, array) => array.indexOf(value) === index);

    if (actionIds.length === 0) {
      const choice = ignore ? 1 : 2;
      this.setMessage({
        success: false,
        title: this.$tc('closed_trades.ignore.no_actions.title', choice),
        description: this.$tc(
          'closed_trades.ignore.no_actions.description',
          choice
        )
      });
      return;
    }
    const payload: IgnoreActionPayload = {
      actionIds: actionIds,
      type: IGNORE_TRADES
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

  @Emit()
  refresh() {}

  @Prop({ required: true })
  data!: TradeEntry[];

  @Watch('data')
  onDataUpdate(newData: TradeEntry[], oldData?: TradeEntry[]) {
    if (oldData && newData.length < oldData.length) {
      this.page = 1;
    }
  }

  newExternalTrade() {
    this.dialogTitle = this.$tc('closed_trades.dialog.add.title');
    this.dialogSubtitle = '';
    this.openDialog = true;
  }

  editTrade(trade: TradeEntry) {
    this.editableItem = trade;
    this.dialogTitle = this.$tc('closed_trades.dialog.edit.title');
    this.dialogSubtitle = this.$tc('closed_trades.dialog.edit.subtitle');
    this.openDialog = true;
  }

  promptForDelete(trade: TradeEntry) {
    const prep = (trade.tradeType === 'buy'
      ? this.$t('closed_trades.description.with').toString()
      : this.$t('closed_trades.description.for').toString()
    ).toLocaleLowerCase();
    this.confirmationMessage = this.$t('closed_trades.confirmation.message', {
      pair: `${this.getSymbol(trade.baseAsset)} ${prep} ${this.getSymbol(
        trade.quoteAsset
      )}`,
      action: trade.tradeType,
      amount: trade.amount
    }).toString();
    this.tradeToDelete = trade;
  }

  async deleteTrade() {
    if (!this.tradeToDelete) {
      return;
    }
    const success: boolean = await this.deleteExternalTrade(
      this.tradeToDelete.tradeId
    );
    if (!success) {
      return;
    }
    this.tradeToDelete = null;
    this.confirmationMessage = '';
  }

  async save() {
    const form = this.$refs.form as ExternalTradeForm;
    const success = await form.save();
    if (success) {
      this.clearDialog();
    }
  }

  clearDialog() {
    (this.$refs.form as ExternalTradeForm).reset();
    this.openDialog = false;
    this.editableItem = null;
  }
}
</script>

<style scoped lang="scss">
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
