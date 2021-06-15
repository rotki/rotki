<template>
  <v-form ref="form" data-cy="exchange-keys" :value="value" @input="input">
    <v-row class="pt-2">
      <v-col cols="12" md="6">
        <v-autocomplete
          outlined
          :value="exchange.location"
          :items="exchanges"
          :label="$t('exchange_keys_form.exchange')"
          data-cy="exchange"
          :disabled="edit"
          @change="onExchangeChange($event)"
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
        </v-autocomplete>
      </v-col>
      <v-col cols="12" md="6">
        <v-text-field
          v-if="edit"
          outlined
          :value="exchange.newName"
          :rules="nameRules"
          data-cy="name"
          :label="$t('exchange_keys_form.name.label')"
          @input="onUpdateExchange({ ...exchange, newName: $event })"
        />
        <v-text-field
          v-else
          outlined
          :value="exchange.name"
          :rules="nameRules"
          data-cy="name"
          :label="$t('exchange_keys_form.name.label')"
          @input="onUpdateExchange({ ...exchange, name: $event })"
        />
      </v-col>
    </v-row>

    <v-select
      v-if="exchange.location === 'kraken'"
      outlined
      :value="exchange.krakenAccountType"
      data-cy="account-type"
      :items="krakenAccountTypes"
      :label="$t('exchange_settings.inputs.kraken_account')"
      @change="onUpdateExchange({ ...exchange, krakenAccountType: $event })"
    />

    <div class="text-subtitle-2 mt-2 pb-4">
      {{ $t('exchange_settings.keys') }}
      <v-tooltip top open-delay="400">
        <template #activator="{ on, attrs }">
          <v-btn icon v-bind="attrs" class="ml-4" v-on="on" @click="toggleEdit">
            <v-icon v-if="!editKeys">mdi-pencil-outline</v-icon>
            <v-icon v-else>mdi-close</v-icon>
          </v-btn>
        </template>
        <span>
          {{
            !editKeys
              ? $t('exchange_keys_form.edit.activate_tooltip')
              : $t('exchange_keys_form.edit.deactivate_tooltip')
          }}
        </span>
      </v-tooltip>
    </div>

    <div class="exchange-keys-form__keys">
      <revealable-input
        outlined
        :disabled="edit && !editKeys"
        :value="exchange.apiKey"
        :rules="!edit || editKeys ? apiKeyRules : []"
        data-cy="api-key"
        :label="$t('exchange_settings.inputs.api_key')"
        @input="onUpdateExchange({ ...exchange, apiKey: $event })"
        @paste="onApiKeyPaste"
      />

      <revealable-input
        outlined
        :disabled="edit && !editKeys"
        :value="exchange.apiSecret"
        :rules="!edit || editKeys ? apiSecretRules : []"
        data-cy="api-secret"
        prepend-icon="mdi-lock"
        :label="$t('exchange_settings.inputs.api_secret')"
        @input="onUpdateExchange({ ...exchange, apiSecret: $event })"
        @paste="onApiSecretPaste"
      />

      <revealable-input
        v-if="requiresPassphrase"
        :disabled="edit && !editKeys"
        outlined
        :value="exchange.passphrase"
        :rules="passphraseRules"
        prepend-icon="mdi-key-plus"
        data-cy="passphrase"
        :label="$t('exchange_settings.inputs.passphrase')"
        @input="onUpdateExchange({ ...exchange, passphrase: $event })"
      />
    </div>

    <div v-if="exchange.location === 'ftx'">
      <v-text-field
        v-if="edit"
        outlined
        :value="exchange.ftxSubaccount"
        data-cy="ftxSubaccount"
        :label="$t('exchange_settings.inputs.ftx_subaccount')"
        @input="onUpdateExchange({ ...exchange, ftxSubaccount: $event })"
      />
      <v-text-field
        v-else
        outlined
        :value="exchange.ftxSubaccount"
        data-cy="ftxSubaccount"
        :label="$t('exchange_settings.inputs.ftx_subaccount')"
        @input="onUpdateExchange({ ...exchange, ftxSubaccount: $event })"
      />
    </div>

    <binance-pairs-selector
      v-if="isBinance & edit"
      :value="binancePairs"
      :name="exchange.name"
      :location="exchange.location"
      @input="onUpdateExchange({ ...exchange, binanceMarkets: $event })"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import ExchangeDisplay from '@/components/display/ExchangeDisplay.vue';
import BinancePairsSelector from '@/components/helper/BinancePairsSelector.vue';
import { tradeLocations } from '@/components/history/consts';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import {
  EXCHANGE_BINANCE,
  EXCHANGE_BINANCEUS,
  EXCHANGE_COINBASEPRO,
  EXCHANGE_KRAKEN,
  EXCHANGE_KUCOIN,
  SUPPORTED_EXCHANGES
} from '@/data/defaults';
import { SupportedExchange } from '@/services/balances/types';
import { KRAKEN_ACCOUNT_TYPES } from '@/store/balances/const';
import { ExchangePayload } from '@/store/balances/types';
import { trimOnPaste } from '@/utils/event';

@Component({
  name: 'ExchangeKeysForm',
  components: { RevealableInput, ExchangeDisplay, BinancePairsSelector },
  computed: {
    ...mapGetters('balances', ['exchangeNonce'])
  }
})
export default class ExchangeKeysForm extends Vue {
  readonly krakenAccountTypes = KRAKEN_ACCOUNT_TYPES;
  readonly exchanges = SUPPORTED_EXCHANGES;
  exchangeNonce!: (exchange: SupportedExchange) => number;

  @Prop({ required: true, type: Boolean })
  value!: boolean;

  @Prop({ required: true })
  exchange!: ExchangePayload;

  @Prop({ required: true, type: Boolean })
  edit!: boolean;

  @Emit('input')
  input(_value: boolean) {}

  @Emit('update:exchange')
  onUpdateExchange(_exchange: ExchangePayload) {}

  binancePairs: string[] = [];
  editKeys: boolean = false;

  toggleEdit() {
    this.editKeys = !this.editKeys;
    if (!this.editKeys) {
      this.onUpdateExchange({
        ...this.exchange,
        apiSecret: null,
        apiKey: null
      });
    }
  }

  readonly nameRules = [
    (v: string) =>
      !!v || this.$t('exchange_keys_form.name.non_empty').toString()
  ];

  readonly apiKeyRules = [
    (v: string) =>
      !!v || this.$t('exchange_keys_form.api_key.non_empty').toString()
  ];

  readonly apiSecretRules = [
    (v: string) =>
      !!v || this.$t('exchange_keys_form.api_secret.non_empty').toString()
  ];

  readonly passphraseRules = [
    (v: string) =>
      !!v || this.$t('exchange_keys_form.passphrase.non_empty').toString()
  ];

  get requiresPassphrase(): boolean {
    const exchange = this.exchange.location;
    return exchange === EXCHANGE_COINBASEPRO || exchange === EXCHANGE_KUCOIN;
  }

  get isBinance(): boolean {
    const exchange = this.exchange.location;
    return exchange === EXCHANGE_BINANCE || exchange === EXCHANGE_BINANCEUS;
  }

  mounted() {
    if (this.edit) {
      return;
    }
    this.onUpdateExchange({
      ...this.exchange,
      name: this.suggestedName(this.exchange.location)
    });
  }

  onExchangeChange(exchange: SupportedExchange) {
    (this.$refs.form as any).reset();
    const name = this.suggestedName(exchange);
    this.onUpdateExchange({
      name: name,
      newName: null,
      location: exchange,
      apiKey: null,
      apiSecret: null,
      passphrase: null,
      krakenAccountType: exchange === EXCHANGE_KRAKEN ? 'starter' : null,
      binanceMarkets: null,
      ftxSubaccount: null
    });
  }

  private suggestedName(exchange: SupportedExchange): string {
    const location = tradeLocations.find(
      ({ identifier }) => identifier === exchange
    );
    return location ? `${location.name} ${this.exchangeNonce(exchange)}` : '';
  }

  onApiKeyPaste(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.onUpdateExchange({ ...this.exchange, apiKey: paste });
    }
  }

  onApiSecretPaste(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.onUpdateExchange({ ...this.exchange, apiSecret: paste });
    }
  }
}
</script>

<style lang="scss" scoped>
::v-deep {
  .exchange-keys-form {
    &__keys {
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

  .v-text-field {
    &--outlined {
      .v-input {
        &__append-inner {
          margin-top: 10px;
        }
      }
    }
  }
}
</style>
