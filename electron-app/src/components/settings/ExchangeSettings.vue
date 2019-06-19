<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-toolbar card>Exchange Settings</v-toolbar>
        <v-card-text>
          <v-layout row class="connected-exchanges">
            <exchange-badge
              v-for="exchange in connectedExchanges"
              :name="exchange"
            ></exchange-badge>
          </v-layout>
          <v-select
            v-model="selectedExchange"
            :items="availableExchanges"
            label="Exchange"
          ></v-select>
          <v-text-field
            id="premium_api_key_entry"
            v-model="apiKey"
            prepend-icon="fa-key"
            label="API Key"
            :disabled="isConnected"
            type="text"
          ></v-text-field>
          <v-text-field
            id="premium_api_secret_entry"
            v-model="apiSecret"
            prepend-icon="fa-user-secret"
            label="API Secret"
            :disabled="isConnected"
            type="text"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn
            id="setup_exchange"
            depressed
            color="primary"
            type="submit"
            @click="clicked()"
          >
            {{ isConnected ? 'Remove' : 'Setup' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-flex>
    <message-dialog
      :title="errorTitle"
      :message="errorMessage"
      @dismiss="dismiss()"
    ></message-dialog>
    <confirm-dialog
      :title="confirmTitle"
      :message="confirmMessage"
      :display="confirmation"
      @cancel="confirmation = false"
      @confirm="remove()"
    ></confirm-dialog>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { exchanges } from '@/data/defaults';
import { mapState } from 'vuex';
import { query_exchange_balances_async } from '@/legacy/exchange';
import ExchangeBadge from '@/components/ExchangeBadge.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';

@Component({
  components: { ConfirmDialog, MessageDialog, ExchangeBadge },
  computed: mapState(['connectedExchanges'])
})
export default class ExchangeSettings extends Vue {
  apiKey: string = '';
  apiSecret: string = '';
  selectedExchange: string = exchanges[0];
  confirmation: boolean = false;

  errorMessage: string = '';
  errorTitle: string = '';

  connectedExchanges!: string[];

  @Watch('selectedExchange')
  onChange() {
    this.resetFields();
  }

  private resetFields(includeExchange: boolean = false) {
    this.apiKey = '';
    this.apiSecret = '';

    if (includeExchange) {
      this.selectedExchange = exchanges[0];
    }
  }

  readonly confirmTitle = 'Confirmation Required';
  readonly confirmMessage =
    'Are you sure you want to delete the API key and secret from rotkehlchen? ' +
    'This action is not undoable and you will need to obtain the key and secret again from the exchange.';

  get availableExchanges(): Array<string> {
    return exchanges;
  }

  get isConnected(): boolean {
    return (
      this.connectedExchanges.findIndex(
        value => value === this.selectedExchange
      ) >= 0
    );
  }

  dismiss() {
    this.errorTitle = '';
    this.errorMessage = '';
  }

  clicked() {
    if (this.isConnected) {
      this.confirmation = true;
      return;
    }

    const exchangeName = this.selectedExchange;
    this.$rpc
      .setup_exchange(exchangeName, this.apiKey, this.apiSecret)
      .then(() => {
        this.resetFields(true);
        this.$store.commit('addExchange', exchangeName);
        query_exchange_balances_async(exchangeName, false);
      })
      .catch((reason: Error) => {
        this.errorTitle = 'Exchange Setup Error';
        this.errorMessage = `Error at setup of ${exchangeName}: ${reason.message}`;
      });
  }

  remove() {
    this.confirmation = false;
    const exchangeName = this.selectedExchange;
    this.$rpc
      .remove_exchange(exchangeName)
      .then(() => {
        this.resetFields(true);
        const exchangeIndex = this.connectedExchanges.findIndex(
          value => value === exchangeName
        );
        if (exchangeIndex === -1) {
          this.errorMessage = 'Error during exchange removal';
          this.errorMessage = `Exchange ${exchangeName} was not in connected_exchanges when trying to remove`;
        } else {
          this.$store.commit('removeExchange', exchangeName);
        }
      })
      .catch((reason: Error) => {
        this.errorTitle = 'Exchange Removal Error';
        this.errorMessage = `Error at removing ${exchangeName} exchange: ${reason.message}`;
      });
  }
}
</script>

<style scoped lang="scss">
.connected-exchanges {
  margin-left: 16px;
  margin-right: 16px;
}
</style>
