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

    <div class="text-subtitle-2">{{ $t('exchange_settings.keys') }}</div>

    <revealable-input
      outlined
      :disabled="edit"
      :value="exchange.apiKey"
      :rules="!edit ? apiKeyRules : []"
      data-cy="api-key"
      :label="$t('exchange_settings.inputs.api_key')"
      @input="onUpdateExchange({ ...exchange, apiKey: $event })"
      @paste="onApiKeyPaste"
    />

    <revealable-input
      outlined
      :disabled="edit"
      :value="exchange.apiSecret"
      :rules="!edit ? apiSecretRules : []"
      data-cy="api-secret"
      prepend-icon="mdi-lock"
      :label="$t('exchange_settings.inputs.api_secret')"
      @input="onUpdateExchange({ ...exchange, apiSecret: $event })"
      @paste="onApiSecretPaste"
    />

    <revealable-input
      v-if="requiresPassphrase"
      outlined
      :value="exchange.passphrase"
      :rules="passphraseRules"
      prepend-icon="mdi-key-plus"
      data-cy="passphrase"
      :label="$t('exchange_settings.inputs.passphrase')"
      @input="onUpdateExchange({ ...exchange, passphrase: $event })"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import ExchangeDisplay from '@/components/display/ExchangeDisplay.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import {
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
  components: { RevealableInput, ExchangeDisplay }
})
export default class ExchangeKeysForm extends Vue {
  readonly krakenAccountTypes = KRAKEN_ACCOUNT_TYPES;
  readonly exchanges = SUPPORTED_EXCHANGES;

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

  onExchangeChange(exchange: SupportedExchange) {
    (this.$refs.form as any).reset();
    this.onUpdateExchange({
      name: '',
      newName: null,
      location: exchange,
      apiKey: '',
      apiSecret: '',
      passphrase: null,
      krakenAccountType: exchange === EXCHANGE_KRAKEN ? 'starter' : null
    });
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
