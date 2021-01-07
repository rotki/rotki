<template>
  <v-row class="exchange-settings">
    <v-col>
      <v-card>
        <v-card-title>{{ $t('exchange_settings.title') }}</v-card-title>
        <v-card-subtitle>
          <i18n path="exchange_settings.subtitle" tag="div">
            <base-external-link
              :text="$t('exchange_settings.usage_guide')"
              :href="$interop.usageGuideURL + '#adding-an-exchange'"
            />
          </i18n>
        </v-card-subtitle>
        <v-card-text>
          <v-row>
            <v-col class="text-h6">
              {{ $t('exchange_settings.connected_exchanges') }}
            </v-col>
          </v-row>
          <v-row class="exchange-settings__connected-exchanges">
            <exchange-badge
              v-for="exchange in connectedExchanges"
              :key="exchange"
              :identifier="exchange"
              class="mr-2"
              removeable
              @remove="confirmRemoval(exchange)"
            />
          </v-row>
          <v-row class="mt-2">
            <v-col class="text-h6">
              {{ $t('exchange_settings.setup_exchange') }}
            </v-col>
          </v-row>
          <v-select
            v-model="selectedExchange"
            class="exchange-settings__fields__exchange"
            :items="exchanges"
            label="Exchange"
          >
            <template #selection="{ item, attrs, on }">
              <exchange-display
                :exchange="item"
                :class="`exchange__${item}`"
                v-bind="attrs"
                v-on="on"
              />
            </template>
            <template #item="{ item, attrs, on }">
              <exchange-display
                :exchange="item"
                :class="`exchange__${item}`"
                v-bind="attrs"
                v-on="on"
              />
            </template>
          </v-select>

          <revealable-input
            v-model="apiKey"
            class="exchange-settings__fields__api-key"
            :label="$t('exchange_settings.inputs.api_key')"
            :disabled="isConnected"
            @paste="onApiKeyPaste"
          />

          <revealable-input
            v-model="apiSecret"
            class="exchange-settings__fields__api-secret"
            prepend-icon="mdi-lock"
            :label="$t('exchange_settings.inputs.api_secret')"
            :disabled="isConnected"
            @paste="onApiSecretPaste"
          />

          <revealable-input
            v-if="selectedExchange === 'coinbasepro'"
            v-model="passphrase"
            prepend-icon="mdi-key-plus"
            class="exchange-settings__fields__passphrase"
            :label="$t('exchange_settings.inputs.passphrase')"
            :disabled="isConnected"
          />

          <v-select
            v-if="selectedExchange === 'kraken'"
            v-model="selectedKrakenAccountType"
            :disabled="isConnected"
            class="exchange-settings__fields__kraken-account-type"
            :items="krakenAccountTypes"
            :label="$t('exchange_settings.inputs.kraken_account')"
            @change="onChangeKrakenAccountType"
          />
        </v-card-text>
        <v-card-actions v-if="!isConnected">
          <v-btn
            class="exchange-settings__buttons__setup"
            depressed
            color="primary"
            type="submit"
            @click="setup()"
          >
            {{ $t('exchange_settings.actions.setup') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-col>
    <confirm-dialog
      :display="confirmation"
      :title="$t('exchange_settings.confirmation.title')"
      :message="
        $t('exchange_settings.confirmation.message', {
          exchange: pendingRemoval
        })
      "
      @cancel="confirmation = false"
      @confirm="remove()"
    />
  </v-row>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ExchangeDisplay from '@/components/display/ExchangeDisplay.vue';
import ExchangeBadge from '@/components/ExchangeBadge.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { EXCHANGE_CRYPTOCOM, exchanges } from '@/data/defaults';
import { SupportedExchange } from '@/services/balances/types';
import { ExchangePayload } from '@/store/balances/types';
import { trimOnPaste } from '@/utils/event';

@Component({
  components: {
    ExchangeDisplay,
    RevealableInput,
    ConfirmDialog,
    ExchangeBadge,
    BaseExternalLink
  },
  computed: {
    ...mapState('balances', ['connectedExchanges']),
    ...mapGetters('session', ['krakenAccountType'])
  },
  methods: {
    ...mapActions('balances', ['setupExchange', 'removeExchange'])
  }
})
export default class ExchangeSettings extends Vue {
  krakenAccountType!: string;
  apiKey: string = '';
  apiSecret: string = '';
  passphrase: string | null = null;
  selectedExchange: string = exchanges[0];
  pendingRemoval: string = '';
  confirmation: boolean = false;

  connectedExchanges!: string[];
  setupExchange!: (payload: ExchangePayload) => Promise<boolean>;
  removeExchange!: (exchange: string) => Promise<boolean>;
  krakenAccountTypes = ['starter', 'intermediate', 'pro'];
  selectedKrakenAccountType = '';

  get exchanges(): SupportedExchange[] {
    return exchanges.filter(
      exchange =>
        !this.connectedExchanges.includes(exchange) &&
        exchange !== EXCHANGE_CRYPTOCOM
    );
  }

  mounted() {
    this.selectedKrakenAccountType = this.krakenAccountType;
  }

  @Watch('selectedExchange')
  onChangeExchange() {
    this.resetFields();
  }

  onApiKeyPaste(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.apiKey = paste;
    }
  }

  onApiSecretPaste(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.apiSecret = paste;
    }
  }

  async onChangeKrakenAccountType() {
    await this.$store.dispatch(
      'session/setKrakenAccountType',
      this.selectedKrakenAccountType
    );
  }

  private resetFields(includeExchange: boolean = false) {
    this.apiKey = '';
    this.apiSecret = '';
    this.passphrase = null;

    if (includeExchange) {
      this.selectedExchange = exchanges[0];
    }
  }

  get isConnected(): boolean {
    return (
      this.connectedExchanges.findIndex(
        value => value === this.selectedExchange
      ) >= 0
    );
  }

  confirmRemoval(exchange: string) {
    this.confirmation = true;
    this.pendingRemoval = exchange;
  }

  async setup() {
    const success = await this.setupExchange({
      exchange: this.selectedExchange,
      apiSecret: this.apiSecret.trim(),
      apiKey: this.apiKey.trim(),
      passphrase: this.passphrase
    });

    if (success) {
      this.resetFields(true);
    }
  }

  async remove() {
    this.confirmation = false;
    const exchange = this.pendingRemoval;
    this.pendingRemoval = '';
    const success = await this.removeExchange(exchange);
    if (success) {
      this.resetFields(true);
    }
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

  &__fields {
    &__exchange {
      ::v-deep {
        .v-select {
          &__selections {
            height: 36px;
          }
        }
      }
    }
  }

  ::v-deep {
    .v-input {
      &--is-disabled {
        .v-icon,
        .v-label {
          color: green !important;
        }
      }
    }
  }
}
</style>
