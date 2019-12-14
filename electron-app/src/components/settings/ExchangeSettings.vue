<template>
  <v-row class="exchange-settings">
    <v-col>
      <v-card>
        <v-card-title>Exchange Settings</v-card-title>
        <v-card-text>
          <v-row class="exchange-settings__connected-exchanges">
            <exchange-badge
              v-for="exchange in connectedExchanges"
              :key="exchange"
              :name="exchange"
            ></exchange-badge>
          </v-row>
          <v-select
            v-model="selectedExchange"
            class="exchange-settings__fields__exchange"
            :items="availableExchanges"
            label="Exchange"
          ></v-select>
          <v-text-field
            v-model="apiKey"
            class="exchange-settings__fields__api-key"
            prepend-icon="fa-key"
            :append-icon="showKey ? 'fa-eye' : 'fa-eye-slash'"
            label="API Key"
            :disabled="isConnected"
            :type="showKey ? 'text' : 'password'"
            @click:append="showKey = !showKey"
          ></v-text-field>
          <v-text-field
            v-model="apiSecret"
            :append-icon="showSecret ? 'fa-eye' : 'fa-eye-slash'"
            :type="showSecret ? 'text' : 'password'"
            class="exchange-settings__fields__api-secret"
            prepend-icon="fa-user-secret"
            label="API Secret"
            :disabled="isConnected"
            @click:append="showSecret = !showSecret"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn
            class="exchange-settings__buttons__setup"
            depressed
            color="primary"
            type="submit"
            @click="clicked()"
          >
            {{ isConnected ? 'Remove' : 'Setup' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-col>
    <confirm-dialog
      :display="confirmation"
      title="Confirmation Required"
      message="Are you sure you want to delete the API key and secret from rotkehlchen? This action can not be undone and you will need to obtain the key and secret again from the exchange."
      @cancel="confirmation = false"
      @confirm="remove()"
    ></confirm-dialog>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { exchanges } from '@/data/defaults';
import { createNamespacedHelpers } from 'vuex';
import ExchangeBadge from '@/components/ExchangeBadge.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { createExchangePayload } from '@/store/balances/actions';
import { Message } from '@/store/store';

const { mapState } = createNamespacedHelpers('balances');

@Component({
  components: { ConfirmDialog, MessageDialog, ExchangeBadge },
  computed: mapState(['connectedExchanges'])
})
export default class ExchangeSettings extends Vue {
  apiKey: string = '';
  apiSecret: string = '';
  selectedExchange: string = exchanges[0];
  confirmation: boolean = false;

  showKey: boolean = false;
  showSecret: boolean = false;

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

  clicked() {
    if (this.isConnected) {
      this.confirmation = true;
      return;
    }

    const exchangeName = this.selectedExchange;
    const { commit, dispatch } = this.$store;
    this.$rpc
      .setup_exchange(exchangeName, this.apiKey, this.apiSecret)
      .then(() => {
        this.resetFields(true);
        commit('balances/addExchange', exchangeName);
        dispatch(
          'balances/fetchExchangeBalances',
          createExchangePayload(exchangeName)
        );
      })
      .catch((reason: Error) => {
        commit('setMessage', {
          title: 'Exchange Setup Error',
          description: `Error at setup of ${exchangeName}: ${reason.message}`
        } as Message);
      });
  }

  remove() {
    const { commit } = this.$store;
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
          commit('setMessage', {
            title: 'Error during exchange removal',
            description: `Exchange ${exchangeName} was not in connected_exchanges when trying to remove`
          } as Message);
        } else {
          commit('balances/removeExchange', exchangeName);
        }
      })
      .catch((reason: Error) => {
        commit('setMessage', {
          title: 'Exchange Removal Error',
          description: `Error at removing ${exchangeName} exchange: ${reason.message}`
        } as Message);
      });
  }
}
</script>

<style scoped lang="scss">
.exchange-settings {
  &__connected-exchanges {
    display: flex;
    flex-direction: row;
    justify-content: flex-start;
    padding: 8px;
  }

  ::v-deep .v-input--is-disabled {
    .v-icon,
    .v-label {
      color: green !important;
    }
  }
}
</style>
