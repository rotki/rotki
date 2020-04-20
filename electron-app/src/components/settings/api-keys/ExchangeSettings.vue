<template>
  <v-row class="exchange-settings">
    <v-col>
      <v-card>
        <v-card-title>Exchanges</v-card-title>
        <v-card-text>
          <p>
            Rotki can connect to supported exchanges and automatically pull your
            your trades and balances from that exchange. See the
            <base-external-link
              :href="$interop.usageGuideURL + '#adding-an-exchange'"
            >
              Usage Guide
            </base-external-link>
            for more information.
          </p>
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
          >
            <template #item="{ item, attrs, on }">
              <v-list-item
                :class="`exchange__${item}`"
                v-bind="attrs"
                v-on="on"
              >
                {{ item }}
              </v-list-item>
            </template>
          </v-select>
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
          <v-text-field
            v-if="selectedExchange === 'coinbasepro'"
            v-model="passphrase"
            class="exchange-settings__fields__passphrase"
            prepend-icon="fa-key"
            :append-icon="showPassphrase ? 'fa-eye' : 'fa-eye-slash'"
            label="Passphrase"
            :disabled="isConnected"
            :type="showKey ? 'text' : 'password'"
            @click:append="showKey = !showKey"
          ></v-text-field>
          <v-select
            v-if="selectedExchange === 'kraken'"
            v-model="selectedKrakenAccountType"
            class=""
            :items="krakenAccountTypes"
            label="Select the type of your Kraken account"
            @change="onChangeKrakenAccountType"
          ></v-select>
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
import { createNamespacedHelpers } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import ExchangeBadge from '@/components/ExchangeBadge.vue';
import { convertToGeneralSettings } from '@/data/converters';
import { exchanges } from '@/data/defaults';
import { Message } from '@/store/store';

const { mapState } = createNamespacedHelpers('balances');
const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { ConfirmDialog, MessageDialog, ExchangeBadge, BaseExternalLink },
  computed: {
    ...mapState(['connectedExchanges']),
    ...mapGetters(['krakenAccountType'])
  }
})
export default class ExchangeSettings extends Vue {
  krakenAccountType!: string;
  apiKey: string = '';
  apiSecret: string = '';
  passphrase: string | null = null;
  selectedExchange: string = exchanges[0];
  confirmation: boolean = false;

  showKey: boolean = false;
  showSecret: boolean = false;
  showPassphrase: boolean = false;

  connectedExchanges!: string[];
  krakenAccountTypes = ['starter', 'intermediate', 'pro'];
  selectedKrakenAccountType = '';

  mounted() {
    this.selectedKrakenAccountType = this.krakenAccountType;
  }

  @Watch('selectedExchange')
  onChangeExchange() {
    this.resetFields();
  }

  onChangeKrakenAccountType() {
    const { commit } = this.$store;
    this.$api
      .setSettings({ kraken_account_type: this.selectedKrakenAccountType })
      .then(settings => {
        commit('setMessage', {
          title: 'Success',
          description: 'Successfully set kraken account type',
          success: true
        } as Message);
        commit('session/settings', convertToGeneralSettings(settings));
      })
      .catch(reason => {
        commit('setMessage', {
          title: 'Error',
          description: `Error setting kraken account type ${reason.message}`
        } as Message);
      });
  }

  private resetFields(includeExchange: boolean = false) {
    this.apiKey = '';
    this.apiSecret = '';
    this.passphrase = null;

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
    this.$api
      .setupExchange(exchangeName, this.apiKey, this.apiSecret, this.passphrase)
      .then(() => {
        this.resetFields(true);
        commit('balances/addExchange', exchangeName);
        dispatch('balances/fetchExchangeBalances', {
          name: exchangeName
        });
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

    this.$api
      .removeExchange(exchangeName)
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
