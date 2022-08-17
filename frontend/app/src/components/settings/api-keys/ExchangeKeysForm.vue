<template>
  <v-form ref="form" data-cy="exchange-keys" :value="value" @input="input">
    <v-row class="pt-2">
      <v-col cols="12" md="6">
        <v-autocomplete
          outlined
          :value="exchange.location"
          :items="exchanges"
          :label="tc('exchange_keys_form.exchange')"
          data-cy="exchange"
          :disabled="edit"
          auto-select-first
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
          :label="tc('common.name')"
          @input="onUpdateExchange({ ...exchange, newName: $event })"
        />
        <v-text-field
          v-else
          outlined
          :value="exchange.name"
          :rules="nameRules"
          data-cy="name"
          :label="tc('common.name')"
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
      :label="tc('exchange_settings.inputs.kraken_account')"
      @change="onUpdateExchange({ ...exchange, krakenAccountType: $event })"
    />

    <div class="text-subtitle-2 mt-2 pb-4">
      {{ tc('exchange_settings.keys') }}
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
              ? tc('exchange_keys_form.edit.activate_tooltip')
              : tc('exchange_keys_form.edit.deactivate_tooltip')
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
        :label="tc('exchange_settings.inputs.api_key')"
        @input="onUpdateExchange({ ...exchange, apiKey: $event })"
        @paste="onApiKeyPaste"
      />

      <revealable-input
        v-if="exchange.location !== 'bitpanda'"
        outlined
        :disabled="edit && !editKeys"
        :value="exchange.apiSecret"
        :rules="!edit || editKeys ? apiSecretRules : []"
        data-cy="api-secret"
        prepend-icon="mdi-lock"
        :label="tc('exchange_settings.inputs.api_secret')"
        @input="onUpdateExchange({ ...exchange, apiSecret: $event })"
        @paste="onApiSecretPaste"
      />

      <revealable-input
        v-if="requiresPassphrase"
        :disabled="edit && !editKeys"
        outlined
        :value="exchange.passphrase"
        :rules="!edit || editKeys ? passphraseRules : []"
        prepend-icon="mdi-key-plus"
        data-cy="passphrase"
        :label="tc('exchange_settings.inputs.passphrase')"
        @input="onUpdateExchange({ ...exchange, passphrase: $event })"
      />
    </div>

    <div v-if="exchange.location === 'ftx' || exchange.location === 'ftxus'">
      <v-text-field
        v-if="edit"
        outlined
        :value="exchange.ftxSubaccount"
        data-cy="ftxSubaccount"
        :label="tc('exchange_settings.inputs.ftx_subaccount')"
        @input="onUpdateExchange({ ...exchange, ftxSubaccount: $event })"
      />
      <v-text-field
        v-else
        outlined
        :value="exchange.ftxSubaccount"
        data-cy="ftxSubaccount"
        :label="tc('exchange_settings.inputs.ftx_subaccount')"
        @input="onUpdateExchange({ ...exchange, ftxSubaccount: $event })"
      />
    </div>

    <binance-pairs-selector
      v-if="isBinance"
      outlined
      :name="exchange.name"
      :location="exchange.location"
      @input="onUpdateExchange({ ...exchange, binanceMarkets: $event })"
    />
  </v-form>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useI18n } from 'vue-i18n-composable';
import ExchangeDisplay from '@/components/display/ExchangeDisplay.vue';
import BinancePairsSelector from '@/components/helper/BinancePairsSelector.vue';
import { tradeLocations } from '@/components/history/consts';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { ExchangePayload } from '@/store/balances/types';
import {
  KrakenAccountType,
  SUPPORTED_EXCHANGES,
  SupportedExchange
} from '@/types/exchanges';
import { trimOnPaste } from '@/utils/event';

export default defineComponent({
  name: 'ExchangeKeysForm',
  components: { RevealableInput, ExchangeDisplay, BinancePairsSelector },
  props: {
    value: { required: true, type: Boolean },
    exchange: { required: true, type: Object as PropType<ExchangePayload> },
    edit: { required: true, type: Boolean }
  },
  emits: ['input', 'update:exchange'],
  setup(props, { emit }) {
    const { edit, exchange } = toRefs(props);
    const editKeys = ref(false);
    const form = ref();

    const { getExchangeNonce } = useExchangeBalancesStore();
    const { tc } = useI18n();

    const requiresPassphrase = computed(() => {
      const { location } = get(exchange);
      return (
        location === SupportedExchange.COINBASEPRO ||
        location === SupportedExchange.KUCOIN
      );
    });

    const isBinance = computed(() => {
      const { location } = get(exchange);
      return (
        location === SupportedExchange.BINANCE ||
        location === SupportedExchange.BINANCEUS
      );
    });

    const nameRules = computed(() => [
      (v: string) => !!v || tc('exchange_keys_form.name.non_empty')
    ]);

    const apiKeyRules = computed(() => [
      (v: string) => !!v || tc('exchange_keys_form.api_key.non_empty')
    ]);

    const apiSecretRules = computed(() => [
      (v: string) => !!v || tc('exchange_keys_form.api_secret.non_empty')
    ]);

    const passphraseRules = computed(() => [
      (v: string) => !!v || tc('exchange_keys_form.passphrase.non_empty')
    ]);

    const suggestedName = function (exchange: SupportedExchange): string {
      const location = tradeLocations.find(
        ({ identifier }) => identifier === exchange
      );
      const nonce = get(getExchangeNonce(exchange));
      return location ? `${location.name} ${nonce}` : '';
    };

    const toggleEdit = () => {
      set(editKeys, !get(editKeys));

      if (!get(editKeys)) {
        onUpdateExchange({
          ...get(exchange),
          apiSecret: null,
          apiKey: null
        });
      }
    };

    const onExchangeChange = (exchange: SupportedExchange) => {
      get(form).reset();
      onUpdateExchange({
        name: suggestedName(exchange),
        newName: null,
        location: exchange,
        apiKey: null,
        apiSecret: exchange === SupportedExchange.BITPANDA ? '' : null,
        passphrase: null,
        krakenAccountType:
          exchange === SupportedExchange.KRAKEN ? 'starter' : null,
        binanceMarkets: null,
        ftxSubaccount: null
      });
    };

    const onApiKeyPaste = function (event: ClipboardEvent) {
      const paste = trimOnPaste(event);
      if (paste) {
        onUpdateExchange({ ...get(exchange), apiKey: paste });
      }
    };

    const onApiSecretPaste = function (event: ClipboardEvent) {
      const paste = trimOnPaste(event);
      if (paste) {
        onUpdateExchange({ ...get(exchange), apiSecret: paste });
      }
    };

    const input = (value: boolean) => {
      emit('input', value);
    };

    const onUpdateExchange = (payload: ExchangePayload) => {
      emit('update:exchange', payload);
    };

    onMounted(() => {
      if (get(edit)) {
        return;
      }
      onUpdateExchange({
        ...get(exchange),
        name: suggestedName(get(exchange).location)
      });
    });

    return {
      krakenAccountTypes: KrakenAccountType.options,
      exchanges: SUPPORTED_EXCHANGES,
      editKeys,
      form,
      requiresPassphrase,
      isBinance,
      nameRules,
      apiKeyRules,
      apiSecretRules,
      passphraseRules,
      input,
      onUpdateExchange,
      onExchangeChange,
      toggleEdit,
      onApiKeyPaste,
      onApiSecretPaste,
      tc
    };
  }
});
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
}
</style>
