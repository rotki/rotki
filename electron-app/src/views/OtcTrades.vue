<template>
  <v-container>
    <otc-form
      :edit-mode="editMode"
      :otc-trade="editableItem"
      @save="saveItem($event)"
      @cancel="cancelEdit()"
    ></otc-form>
    <v-row>
      <v-col>
        <h1>OTC Trades List</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-data-table
            class="otc-trades"
            :headers="headers"
            :items="otcTrades"
            :expanded.sync="expanded"
            single-expand
            show-expand
            item-key="trade_id"
          >
            <template #item.pair="{ item }" class="trade">
              <span class="otc-trades__trade__pair">{{ item.pair }}</span>
            </template>
            <template #item.trade_type="{ item }">
              <span class="otc-trades__trade__type">{{ item.trade_type }}</span>
            </template>
            <template #item.amount="{ item }">
              <span class="otc-trades__trade__amount">{{ item.amount }}</span>
            </template>
            <template #item.rate="{ item }">
              <span class="otc-trades__trade__rate">{{ item.rate }}</span>
            </template>
            <template #item.timestamp="{ item }">
              <span class="otc-trades__trade__time">
                {{ item.timestamp | formatDate(dateDisplayFormat) }}
              </span>
            </template>
            <template #item.actions="{ item }">
              <span class="otc-trades__trade__actions">
                <v-icon
                  small
                  class="mr-2 otc-trades__trade__actions__edit"
                  @click="editItem(item)"
                >
                  fa-edit
                </v-icon>
                <v-icon
                  class="otc-trades__trade__actions__delete"
                  small
                  @click="askForDeleteConfirmation(item)"
                >
                  fa-trash
                </v-icon>
              </span>
            </template>
            <template #expanded-item="{ headers, item }">
              <td :colspan="headers.length">
                <v-col cols="12">
                  <v-row>
                    <h2>Details</h2>
                  </v-row>
                  <v-row v-if="item.notes">
                    <span class="font-weight-medium">Extra Info:</span>
                    {{ item.notes }}
                  </v-row>
                  <v-row v-if="item.link">
                    <span class="font-weight-medium">Links:</span>
                    {{ item.link }}
                  </v-row>
                  <v-row v-if="item.fee">
                    <span class="font-weight-medium">Fee:</span>
                    {{ item.fee }} {{ item.fee_currency }}
                  </v-row>
                </v-col>
              </td>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>
    <confirm-dialog
      v-if="displayConfirmation"
      message="Are you sure you want to delete the trade"
      title="Delete OTC Trade"
      display
      @cancel="cancelConfirmation()"
      @confirm="deleteItem()"
    ></confirm-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { StoredTrade, TradePayload } from '@/model/stored-trade';
import OtcForm from '@/components/OtcForm.vue';
import { createNamespacedHelpers } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { Message } from '@/store/store';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { assert } from '@/utils/assertions';

const { mapGetters } = createNamespacedHelpers('session');
@Component({
  components: { ConfirmDialog, MessageDialog, OtcForm },
  computed: mapGetters(['dateDisplayFormat'])
})
export default class OtcTrades extends Vue {
  dateDisplayFormat!: string;
  expanded = [];
  editMode: boolean = false;
  displayConfirmation: boolean = false;

  deleteId: string = '';
  editableItem: TradePayload | null = null;

  otcTrades: StoredTrade[] = [];

  readonly headers = [
    { text: 'Pair', value: 'pair' },
    { text: 'Type', value: 'trade_type' },
    { text: 'Amount', value: 'amount' },
    { text: 'Rate', value: 'rate' },
    { text: 'Time', value: 'timestamp' },
    { text: 'Actions', value: 'actions', width: '50' },
    { text: '', value: 'data-table-expand' }
  ];

  saveItem(trade: TradePayload) {
    const onFulfilled = () => {
      this.$store.commit('setMessage', {
        title: 'Success',
        description: 'Trade was submitted successfully',
        success: true
      } as Message);
      this.fetchData();
    };
    const onRejected = (reason: Error) => {
      this.editableItem = trade;
      this.$store.commit('setMessage', {
        title: 'Failure',
        description: `Trade Addition Error: ${reason.message}`
      } as Message);
    };

    let promise: Promise<StoredTrade[]>;
    if (this.editMode) {
      assert(trade.trade_id != null);
      promise = this.$api.editExternalTrade(trade as StoredTrade);
    } else {
      promise = this.$api.addExternalTrade(trade);
    }

    promise
      .then(onFulfilled)
      .catch(onRejected)
      .finally(() => this.cancelEdit());
  }

  editItem(item: StoredTrade) {
    this.editMode = true;
    this.editableItem = item;
  }

  askForDeleteConfirmation(item: StoredTrade) {
    this.deleteId = item.trade_id;
    this.displayConfirmation = true;
    this.cancelEdit();
  }

  cancelConfirmation() {
    this.deleteId = '';
    this.displayConfirmation = false;
  }

  deleteItem() {
    this.displayConfirmation = false;
    this.$api
      .deleteExternalTrade(this.deleteId)
      .then(() => {
        this.$store.commit('setMessage', {
          title: 'Success',
          description: 'Trade was deleted successfully',
          success: true
        } as Message);
        const index = this.otcTrades.findIndex(
          value => value.trade_id === this.deleteId
        );
        if (index >= 0) {
          this.otcTrades.splice(index, 1);
        }
      })
      .catch((reason: Error) => {
        this.$store.commit('setMessage', {
          title: 'Failure',
          description: `Error at Trade Deletion: ${reason.message}`
        } as Message);
      })
      .finally(() => {
        this.deleteId = '';
      });
  }

  cancelEdit() {
    this.editMode = false;
    this.editableItem = null;
  }

  created() {
    this.fetchData();
  }

  private fetchData() {
    this.$api
      .queryExternalTrades()
      .then(value => {
        this.otcTrades = value;
      })
      .catch(reason => {
        this.$store.commit('setMessage', {
          title: 'Failure',
          description: `OTC Trade loading failed: ${reason.message}`
        } as Message);
      });
  }
}
</script>

<style scoped></style>
