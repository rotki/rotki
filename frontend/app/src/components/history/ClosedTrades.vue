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
          <v-spacer />
          <refresh-button
            :loading="refreshing"
            :tooltip="$t('closed_trades.refresh_tooltip')"
            @refresh="refresh"
          />
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
            :page.sync="page"
            :loading="refreshing"
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
import { Component, Emit, Mixins, Prop, Watch } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters } from 'vuex';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import OtcForm from '@/components/OtcForm.vue';
import { footerProps } from '@/config/datatable.common';
import StatusMixin from '@/mixins/status-mixin';
import { Trade } from '@/services/history/types';
import { Section } from '@/store/const';

@Component({
  components: {
    RefreshButton,
    UpgradeRow,
    DateDisplay,
    LocationDisplay,
    OtcForm,
    ConfirmDialog,
    BigDialog
  },
  computed: {
    ...mapGetters('history', ['tradesTotal', 'tradesLimit'])
  },
  methods: {
    ...mapActions('history', ['deleteExternalTrade'])
  }
})
export default class ClosedTrades extends Mixins(StatusMixin) {
  readonly headersClosed: DataTableHeader[] = [
    {
      text: this.$tc('closed_trades.headers.location'),
      value: 'location'
    },
    {
      text: this.$tc('closed_trades.headers.action'),
      value: 'tradeType',
      width: '90px'
    },
    { text: this.$tc('closed_trades.headers.pair'), value: 'pair' },
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
      text: this.$tc('closed_trades.headers.fee'),
      value: 'fee',
      align: 'end'
    },
    {
      text: this.$tc('closed_trades.headers.timestamp'),
      value: 'timestamp'
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
  tradesLimit!: number;
  tradesTotal!: number;
  expanded = [];
  page: number = 1;

  deleteExternalTrade!: (tradeId: string) => Promise<boolean>;
  section = Section.TRADES;

  @Emit()
  refresh() {}

  @Prop({ required: true })
  data!: Trade[];

  @Watch('data')
  onDataUpdate(newData: Trade[], oldData?: Trade[]) {
    if (oldData && newData.length < oldData.length) {
      this.page = 1;
    }
  }

  newExternalTrade() {
    this.dialogTitle = this.$tc('closed_trades.dialog.add.title');
    this.dialogSubtitle = '';
    this.openDialog = true;
  }

  editTrade(trade: Trade) {
    this.editableItem = trade;
    this.dialogTitle = this.$tc('closed_trades.dialog.edit.title');
    this.dialogSubtitle = this.$tc('closed_trades.dialog.edit.subtitle');
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
