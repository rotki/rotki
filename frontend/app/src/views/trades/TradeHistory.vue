<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <div class="mx-4 py-2">
            <v-autocomplete
              v-model="selectedLocation"
              :items="tradeLocations"
              hide-details
              hide-selected
              hide-no-data
              clearable
              label="Filter location"
              item-text="name"
              item-value="identifier"
            >
              <template #selection="data">
                <span>
                  <v-img
                    width="36px"
                    contain
                    position="left"
                    max-height="24px"
                    :src="data.item.icon"
                  />
                </span>
                <span>
                  {{ data.item.name }}
                </span>
              </template>
              <template #item="data">
                <span>
                  <v-img
                    width="36px"
                    contain
                    position="left"
                    max-height="24px"
                    :src="data.item.icon"
                  />
                </span>
                <span>
                  {{ data.item.name }}
                </span>
              </template>
            </v-autocomplete>
          </div>
          <v-card-text>
            {{
              selectedLocation
                ? `Showing results for location(s): ${selectedLocation}`
                : 'Showing results across all locations'
            }}
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row class="mt-8">
      <v-col cols="12">
        <v-card>
          <v-btn
            absolute
            fab
            top
            right
            dark
            color="primary"
            class="trades__add-external-trade"
            @click="newExternalTrade()"
          >
            <v-icon>
              fa fa-plus
            </v-icon>
          </v-btn>
          <v-card-title>
            Closed Orders
          </v-card-title>
          <v-card-text>
            <v-data-table
              :items="tableData(externalTrades)"
              :headers="headersClosed"
              :expanded.sync="expanded"
              single-expand
              show-expand
              sort-by="timestamp"
              sort-desc
              class="trades__closed-trades"
              item-key="tradeId"
            >
              <template #item.rate="{ item }">
                <amount-display
                  class="trades__closed-trades__trade__rate"
                  :value="item.rate"
                ></amount-display>
              </template>
              <template #item.amount="{ item }">
                <amount-display
                  class="trades__closed-trades__trade__amount"
                  :value="item.amount"
                ></amount-display>
              </template>
              <template #item.fee="{ item }">
                <amount-display
                  class="trades__closed-trades__trade__fee"
                  :value="item.fee"
                ></amount-display>
              </template>
              <template #item.timestamp="{ item }">
                <span class="trades__closed-trades__trade__time">
                  {{ item.timestamp | formatDate(dateDisplayFormat) }}
                </span>
              </template>
              <template #item.actions="{ item }">
                <div v-if="item.location === 'external'">
                  <v-btn icon>
                    <v-icon
                      small
                      class="trades__closed-trades__trade__actions__edit"
                      @click="editTrade(item)"
                    >
                      fa-edit
                    </v-icon>
                  </v-btn>
                  <v-btn icon>
                    <v-icon
                      class="trades__closed-trades__trade__actions__delete"
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
                  class="trades__closed-trades__trade__details"
                >
                  <v-col cols="12">
                    <v-row>
                      <span class="text-subtitle-2">Trade Details</span>
                    </v-row>
                    <v-row>
                      <v-col cols="1" class="font-weight-medium">
                        Fee
                      </v-col>
                      <v-col cols="1">
                        <amount-display
                          class="trades__closed-trades__trade__fee"
                          show
                          :asset="item.feeCurrency"
                          :value="item.fee"
                        ></amount-display>
                      </v-col>
                      <v-col cols="1" class="font-weight-medium">
                        Notes
                      </v-col>
                      <v-col>
                        {{ item.notes ? item.notes : 'Trade has no notes.' }}
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col cols="1" class="font-weight-medium">
                        Link
                      </v-col>
                      <v-col>
                        {{ item.link ? item.link : 'Trade has no link.' }}
                      </v-col>
                    </v-row>
                  </v-col>
                </td>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Open Orders
          </v-card-title>
          <v-card-text>
            <v-data-table :items="data" :headers="headersOpen"> </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      primary-action="Save"
      @confirm="save()"
      @cancel="clearDialog()"
    >
      <otc-form ref="dialogChild" :edit="editableItem"></otc-form>
    </big-dialog>
    <confirm-dialog
      :display="tradeToDelete !== null"
      title="Delete Trade"
      confirm-type="warning"
      :message="confirmationMessage"
      @cancel="tradeToDelete = null"
      @confirm="deleteTrade()"
    ></confirm-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import OtcForm from '@/components/OtcForm.vue';
import { Trade } from '@/store/trades/types';

export type TradeLocation =
  | 'kraken'
  | 'poloniex'
  | 'bitmex'
  | 'binance'
  | 'bittrex'
  | 'gemini'
  | 'coinbase'
  | 'coinbasepro'
  | 'ethereum'
  | 'bitcoin'
  | 'external';

@Component({
  components: { AmountDisplay, BigDialog, ConfirmDialog, OtcForm },
  computed: {
    ...mapState('trades', ['externalTrades']),
    ...mapGetters('session', ['dateDisplayFormat'])
  },
  methods: {
    ...mapActions('trades', ['fetchExternalTrades', 'deleteExternalTrade'])
  }
})
export default class TradeHistory extends Vue {
  selectedLocation: TradeLocation | null = null;
  expanded = [];
  dialogTitle: string = '';
  dialogSubtitle: string = '';
  openDialog: boolean = false;
  editableItem: Trade | null = null;
  tradeToDelete: Trade | null = null;
  confirmationMessage: string = '';
  dateDisplayFormat!: string;
  fetchExternalTrades!: () => Promise<void>;
  deleteExternalTrade!: (tradeId: string) => Promise<boolean>;

  async clearDialog() {
    interface dataForm extends Vue {
      resetFields(): void;
    }
    const form = this.$refs.dialogChild as dataForm;
    form.resetFields();
    this.openDialog = false;
    this.editableItem = null;
  }

  async save() {
    interface dataForm extends Vue {
      saveTrade(): Promise<boolean>;
    }
    const form = this.$refs.dialogChild as dataForm;
    form.saveTrade().then(success => {
      if (success === true) this.clearDialog();
    });
  }

  // TODO: Use the new action & trades store to grab the external trades & merge w/ the dummy data

  tableData(source: any[]): any[] {
    if (!this.selectedLocation) {
      return source;
    }
    return source.filter(order => {
      return order.location === this.selectedLocation;
    });
  }

  mounted() {
    this.fetchExternalTrades();
  }

  newExternalTrade() {
    this.dialogTitle = 'Add External Trade';
    this.dialogSubtitle = '';
    this.openDialog = true;
  }

  editTrade(trade: Trade) {
    this.editableItem = trade;
    this.dialogTitle = 'Edit External Trade';
    this.dialogSubtitle = 'Edit an existing trade';
    this.openDialog = true;
  }

  promptForDelete(trade: Trade) {
    this.confirmationMessage = `Are you sure you want to delete trade id: ${trade.tradeId}`;
    this.tradeToDelete = trade;
  }

  async deleteTrade() {
    if (this.tradeToDelete) {
      const success: boolean = await this.deleteExternalTrade(
        this.tradeToDelete.tradeId
      );
      if (success) {
        this.tradeToDelete = null;
        this.confirmationMessage = '';
      }
    }
  }

  tradeLocations = [
    {
      identifier: 'kraken',
      name: 'Kraken',
      icon: require('@/assets/images/kraken.png')
    },
    {
      identifier: 'bittrex',
      name: 'Bittrex',
      icon: require('@/assets/images/bittrex.png')
    },
    {
      identifier: 'binance',
      name: 'Binance',
      icon: require('@/assets/images/binance.png')
    },
    {
      identifier: 'gemini',
      name: 'Gemini',
      icon: require('@/assets/images/gemini.png')
    },
    {
      identifier: 'external',
      name: 'External'
    }
  ];

  data = [
    {
      tradeType: 'buy',
      pair: 'ETH_USD',
      amount: 2474.4,
      fee: 79.82,
      rate: 3.05,
      feeCurrency: 'USD',
      location: 'gemini'
    },
    {
      tradeType: 'sell',
      pair: 'BTC_EUR',
      amount: 3224.02,
      fee: 49.1,
      rate: 3.03,
      feeCurrency: 'USD',
      location: 'kraken'
    },
    {
      tradeType: 'buy',
      pair: 'ETH_USD',
      amount: 2674.45,
      fee: 37.13,
      rate: 0.96,
      feeCurrency: 'USD',
      location: 'external'
    },
    {
      tradeType: 'buy',
      pair: 'ETH_USD',
      amount: 2549.32,
      fee: 22.85,
      rate: 4.44,
      feeCurrency: 'USD',
      location: 'kraken'
    },
    {
      tradeType: 'sell',
      pair: 'BTC_USD',
      amount: 2735.45,
      fee: 96.42,
      rate: 2.4,
      feeCurrency: 'USD',
      location: 'kraken'
    },
    {
      tradeType: 'buy',
      pair: 'ETH_USD',
      amount: 2013.89,
      fee: 79.99,
      rate: 4.05,
      feeCurrency: 'USD',
      location: 'bittrex'
    },
    {
      tradeType: 'buy',
      pair: 'ETH_EUR',
      amount: 2819.65,
      fee: 54.89,
      rate: 2.83,
      feeCurrency: 'USD',
      location: 'binance'
    },
    {
      tradeType: 'sell',
      pair: 'BTC_EUR',
      amount: 3858.01,
      fee: 20.91,
      rate: 0.2,
      feeCurrency: 'USD',
      location: 'kraken'
    }
  ];

  dataClosed = [
    {
      tradeType: 'sell',
      pair: 'BTC_EUR',
      amount: 2365.78,
      fee: 56.65,
      rate: 1.12,
      feeCurrency: 'USD',
      timestamp: '2015-06-28T02:51:54 -02:00',
      location: 'kraken'
    },
    {
      tradeType: 'buy',
      pair: 'ETH_EUR',
      amount: 3048.58,
      fee: 31.56,
      rate: 0.95,
      feeCurrency: 'USD',
      timestamp: '2014-08-14T07:09:41 -02:00',
      location: 'external'
    },
    {
      tradeType: 'buy',
      pair: 'ETH_USD',
      amount: 3069.84,
      fee: 26.74,
      rate: 3.66,
      feeCurrency: 'USD',
      timestamp: '2017-01-27T09:33:46 -01:00',
      location: 'binance'
    },
    {
      tradeType: 'buy',
      pair: 'ETH_EUR',
      amount: 2744.72,
      fee: 77.65,
      rate: 1.07,
      feeCurrency: 'USD',
      timestamp: '2017-08-13T10:47:56 -02:00',
      location: 'kraken'
    },
    {
      tradeType: 'buy',
      pair: 'ADA_EUR',
      amount: 1376.63,
      fee: 60.61,
      rate: 1.98,
      feeCurrency: 'USD',
      timestamp: '2014-12-10T08:42:06 -01:00',
      location: 'bittrex'
    },
    {
      tradeType: 'sell',
      pair: 'DAI_ETH',
      amount: 3247.12,
      fee: 90.11,
      rate: 1.96,
      feeCurrency: 'USD',
      timestamp: '2014-12-12T06:19:23 -01:00',
      location: 'binance'
    },
    {
      tradeType: 'sell',
      pair: 'BTC_EUR',
      amount: 1074.99,
      fee: 70.36,
      rate: 3.94,
      feeCurrency: 'USD',
      timestamp: '2014-08-08T05:50:18 -02:00',
      location: 'external'
    },
    {
      tradeType: 'buy',
      pair: 'BTC_EUR',
      amount: 3941.6,
      fee: 82.7,
      rate: 1.45,
      feeCurrency: 'USD',
      timestamp: '2017-06-18T12:04:09 -02:00',
      location: 'gemini'
    },
    {
      tradeType: 'sell',
      pair: 'BTC_USD',
      amount: 2912.6,
      fee: 89.38,
      rate: 1.74,
      feeCurrency: 'USD',
      timestamp: '2020-03-01T06:23:43 -01:00',
      location: 'external'
    }
  ];

  headersClosed = [
    { text: 'Location', value: 'location' },
    { text: 'Action', value: 'tradeType' },
    { text: 'Pair', value: 'pair' },
    { text: 'Rate', value: 'rate', align: 'end' },
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'Fee', value: 'fee', align: 'end' },
    { text: 'Fee Currency', value: 'feeCurrency' },
    { text: 'Timestamp', value: 'timestamp' },
    { text: 'Actions', value: 'actions', width: '110', sortable: false },
    { text: '', value: 'data-table-expand' }
  ];

  headersOpen = [
    { text: 'Location', value: 'location' },
    { text: 'Action', value: 'tradeType' },
    { text: 'Pair', value: 'pair', align: 'end' },
    { text: 'Rate', value: 'rate', align: 'end' },
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'Fee', value: 'fee', align: 'end' },
    { text: 'Fee Currency', value: 'feeCurrency', align: 'end' }
  ];
}
</script>

<style scoped lang="scss">
.trades {
  &__closed-trades {
    &__trade {
      &__details {
        box-shadow: inset 1px 8px 10px -10px;
        background-color: var(--v-rotki-light-grey-base);
      }
    }
  }
}
</style>
