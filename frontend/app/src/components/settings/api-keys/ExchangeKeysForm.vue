<template>
  <v-form data-cy="exchange-keys">
    <v-select
      v-model="selectedExchange"
      :items="exchanges"
      :label="$t('exchange_keys_form.exchange')"
      data-cy="exchange"
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

    <v-text-field
      v-model="name"
      data-cy="name"
      :label="$t('exchange_keys_form.name')"
    />

    <revealable-input
      v-model="apiKey"
      data-cy="api-key"
      :label="$t('exchange_settings.inputs.api_key')"
      @paste="onApiKeyPaste"
    />

    <revealable-input
      v-model="apiSecret"
      data-cy="api-secret"
      prepend-icon="mdi-lock"
      :label="$t('exchange_settings.inputs.api_secret')"
      @paste="onApiSecretPaste"
    />

    <revealable-input
      v-if="requiresPassphrase"
      v-model="passphrase"
      prepend-icon="mdi-key-plus"
      data-cy="passphrase"
      :label="$t('exchange_settings.inputs.passphrase')"
    />

    <v-select
      v-if="selectedExchange === 'kraken'"
      v-model="selectedKrakenAccountType"
      data-cy="account-type"
      :items="krakenAccountTypes"
      :label="$t('exchange_settings.inputs.kraken_account')"
      @change="onChangeKrakenAccountType"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import ExchangeDisplay from '@/components/display/ExchangeDisplay.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import {
  EXCHANGE_COINBASEPRO,
  EXCHANGE_KUCOIN,
  SUPPORTED_EXCHANGES
} from '@/data/defaults';
import { Exchange } from '@/model/action-result';
import { SupportedExchange } from '@/services/balances/types';
import { KRAKEN_ACCOUNT_TYPES } from '@/store/balances/const';
import { KrakenAccountType } from '@/store/balances/types';
import { Nullable } from '@/types';
import { trimOnPaste } from '@/utils/event';

@Component({
  name: 'ExchangeKeysForm',
  components: { RevealableInput, ExchangeDisplay }
})
export default class ExchangeKeysForm extends Vue {
  apiKey: string = '';
  apiSecret: string = '';
  passphrase: string | null = null;
  selectedExchange: SupportedExchange = SUPPORTED_EXCHANGES[0];
  readonly krakenAccountTypes = KRAKEN_ACCOUNT_TYPES;
  selectedKrakenAccountType: Nullable<KrakenAccountType> = null;

  @Prop({ required: true })
  exchange!: Exchange;

  @Emit('update:exchange')
  get requiresPassphrase(): boolean {
    const exchange = this.selectedExchange;
    return exchange === EXCHANGE_COINBASEPRO || exchange === EXCHANGE_KUCOIN;
  }

  get exchanges(): SupportedExchange[] {
    return SUPPORTED_EXCHANGES.filter(
      exchange => !this.connectedExchanges.includes(exchange)
    );
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
      this.selectedExchange = SUPPORTED_EXCHANGES[0];
    }
  }
}
</script>

<style scoped lang="scss"></style>
