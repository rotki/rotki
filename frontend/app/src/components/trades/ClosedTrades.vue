<template>
  <v-row>
    <v-col cols="12">
      <v-card>
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
          <v-icon>
            mdi-plus
          </v-icon>
        </v-btn>
        <v-card-title>
          {{ $t('closed_trades.title') }}
        </v-card-title>
        <v-card-text>
          <v-data-table
            :items="data"
            :headers="headersClosed"
            :expanded.sync="expanded"
            single-expand
            show-expand
            sort-by="timestamp"
            sort-desc
            :footer-props="footerProps"
            class="closed-trades"
            item-key="tradeId"
          >
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
            <template #item.fee="{ item }">
              <amount-display
                class="closed-trades__trade__fee"
                :asset="item.feeCurrency"
                :value="item.fee"
              />
            </template>
            <template #item.timestamp="{ item }">
              <date-display :timestamp="item.timestamp" />
            </template>
            <template #item.actions="{ item }">
              <div v-if="item.location === 'external'">
                <v-btn icon>
                  <v-icon
                    small
                    class="closed-trades__trade__actions__edit"
                    @click="editTrade(item)"
                  >
                    fa-edit
                  </v-icon>
                </v-btn>
                <v-btn icon>
                  <v-icon
                    class="closed-trades__trade__actions__delete"
                    small
                    @click="promptForDelete(item)"
                  >
                    fa-trash
                  </v-icon>
                </v-btn>
              </div>
            </template>
            <template #expanded-item="{ headers, item }">
              <td
                :colspan="headers.length"
                class="closed-trades__trade__details"
              >
                <v-col cols="12">
                  <v-row>
                    <span class="text-subtitle-2">
                      {{ $t('closed_trades.details.title') }}
                    </span>
                  </v-row>
                  <v-row>
                    <v-col>
                      <v-card outlined>
                        <v-card-title class="subtitle-2">
                          {{ $t('closed_trades.details.notes') }}
                        </v-card-title>
                        <v-card-text>
                          {{
                            item.notes
                              ? item.notes
                              : $t('closed_trades.details.note_data')
                          }}
                        </v-card-text>
                      </v-card>
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
                </v-col>
              </td>
            </template>
            <template
              v-if="limit <= total && total !== 0"
              #body.append="{ headers }"
            >
              <upgrade-row
                :limit="limit"
                :total="total"
                :colspan="headers.length"
                :label="$t('closed_trades.label')"
              />
            </template>
          </v-data-table>
        </v-card-text>
      </v-card>
      <big-dialog
        :display="openDialog"
        :title="dialogTitle"
        :subtitle="dialogSubtitle"
        :primary-action="$t('closed_trades.dialog.save')"
        @confirm="save()"
        @cancel="clearDialog()"
      >
        <otc-form ref="form" :edit="editableItem" />
      </big-dialog>
      <confirm-dialog
        :display="tradeToDelete !== null"
        :title="$t('closed_trades.confirmation.title')"
        confirm-type="warning"
        :message="confirmationMessage"
        @cancel="tradeToDelete = null"
        @confirm="deleteTrade()"
      />
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapState } from 'vuex';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import OtcForm from '@/components/OtcForm.vue';
import LocationDisplay from '@/components/trades/LocationDisplay.vue';
import { footerProps } from '@/config/datatable.common';
import { Trade } from '@/services/trades/types';
import UpgradeRow from '@/views/trades/UpgradeRow.vue';

@Component({
  components: {
    UpgradeRow,
    DateDisplay,
    LocationDisplay,
    OtcForm,
    ConfirmDialog,
    BigDialog
  },
  computed: {
    ...mapState('trades', ['total', 'limit'])
  },
  methods: {
    ...mapActions('trades', ['deleteExternalTrade'])
  }
})
export default class ClosedTrades extends Vue {
  readonly headersClosed: DataTableHeader[] = [
    {
      text: this.$t('closed_trades.headers.location').toString(),
      value: 'location',
      width: '40px'
    },
    {
      text: this.$t('closed_trades.headers.action').toString(),
      value: 'tradeType',
      width: '90px'
    },
    { text: this.$t('closed_trades.headers.pair').toString(), value: 'pair' },
    {
      text: this.$t('closed_trades.headers.rate').toString(),
      value: 'rate',
      align: 'end'
    },
    {
      text: this.$t('closed_trades.headers.amount').toString(),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$t('closed_trades.headers.fee').toString(),
      value: 'fee',
      align: 'end'
    },
    {
      text: this.$t('closed_trades.headers.timestamp').toString(),
      value: 'timestamp'
    },
    {
      text: this.$t('closed_trades.headers.actions').toString(),
      value: 'actions',
      width: '110',
      sortable: false
    },
    { text: '', value: 'data-table-expand' }
  ];
  footerProps = footerProps;

  dialogTitle: string = '';
  dialogSubtitle: string = '';
  openDialog: boolean = false;
  editableItem: Trade | null = null;
  tradeToDelete: Trade | null = null;
  confirmationMessage: string = '';
  limit!: number;
  total!: number;
  expanded = [];

  deleteExternalTrade!: (tradeId: string) => Promise<boolean>;

  @Prop({ required: true })
  data!: Trade[];

  newExternalTrade() {
    this.dialogTitle = this.$t('closed_trades.dialog.add.title').toString();
    this.dialogSubtitle = '';
    this.openDialog = true;
  }

  editTrade(trade: Trade) {
    this.editableItem = trade;
    this.dialogTitle = this.$t('closed_trades.dialog.edit.title').toString();
    this.dialogSubtitle = this.$t(
      'closed_trades.dialog.edit.subtitle'
    ).toString();
    this.openDialog = true;
  }

  promptForDelete(trade: Trade) {
    this.confirmationMessage = this.$t('closed_trades.confirmation.message', {
      pair: trade.pair,
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
    const form = this.$refs.form as OtcForm;
    const success = await form.save();
    if (success) {
      this.clearDialog();
    }
  }

  clearDialog() {
    (this.$refs.form as OtcForm).reset();
    this.openDialog = false;
    this.editableItem = null;
  }
}
</script>

<style scoped lang="scss">
.closed-trades {
  &__trade {
    &__details {
      box-shadow: inset 1px 8px 10px -10px;
      background-color: var(--v-rotki-light-grey-base);
    }
  }
}
</style>
