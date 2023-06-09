<script setup lang="ts">
import { helpers, requiredIf, requiredUnless } from '@vuelidate/validators';
import {
  type ExchangePayload,
  KrakenAccountType,
  SUPPORTED_EXCHANGES,
  SupportedExchange
} from '@/types/exchanges';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  exchange: ExchangePayload;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', value: ExchangePayload): void;
}>();

const { editMode, exchange } = toRefs(props);
const editKeys = ref(false);
const form = ref();

const { getExchangeNonce } = useExchangesStore();
const { t } = useI18n();

const requiresApiSecret = computed(() => {
  const { location } = get(exchange);

  return ![SupportedExchange.BITPANDA].includes(location);
});

const requiresPassphrase = computed(() => {
  const { location } = get(exchange);
  return [
    SupportedExchange.COINBASEPRO,
    SupportedExchange.KUCOIN,
    SupportedExchange.OKX
  ].includes(location);
});

const isBinance = computed(() => {
  const { location } = get(exchange);
  return [SupportedExchange.BINANCE, SupportedExchange.BINANCEUS].includes(
    location
  );
});

const { getLocationData } = useLocations();

const suggestedName = function (exchange: SupportedExchange): string {
  const location = getLocationData(exchange);
  const nonce = get(getExchangeNonce(exchange));
  return location ? `${location.name} ${nonce}` : '';
};

const toggleEdit = () => {
  set(editKeys, !get(editKeys));

  if (!get(editKeys)) {
    input({
      ...get(exchange),
      apiSecret: null,
      apiKey: null
    });
  }
};

const onExchangeChange = (exchange: SupportedExchange) => {
  get(form).reset();

  input({
    name: suggestedName(exchange),
    newName: null,
    location: exchange,
    apiKey: null,
    apiSecret: exchange === SupportedExchange.BITPANDA ? '' : null,
    passphrase: null,
    krakenAccountType: exchange === SupportedExchange.KRAKEN ? 'starter' : null,
    binanceMarkets: null,
    ftxSubaccount: null
  });
};

const onApiKeyPaste = function (event: ClipboardEvent) {
  const paste = trimOnPaste(event);
  if (paste) {
    input({ ...get(exchange), apiKey: paste });
  }
};

const onApiSecretPaste = function (event: ClipboardEvent) {
  const paste = trimOnPaste(event);
  if (paste) {
    input({ ...get(exchange), apiSecret: paste });
  }
};

const input = (payload: ExchangePayload) => {
  emit('input', payload);
};

onMounted(() => {
  if (get(editMode)) {
    return;
  }
  input({
    ...get(exchange),
    name: suggestedName(get(exchange).location)
  });
});

const krakenAccountTypes = KrakenAccountType.options;
const exchanges = SUPPORTED_EXCHANGES;

const sensitiveFieldEditable = computed(() => !get(editMode) || get(editKeys));

const rules = {
  name: {
    required: helpers.withMessage(
      t('exchange_keys_form.name.non_empty'),
      requiredUnless(editMode)
    )
  },
  newName: {
    required: helpers.withMessage(
      t('exchange_keys_form.name.non_empty'),
      requiredIf(editMode)
    )
  },
  apiKey: {
    required: helpers.withMessage(
      t('exchange_keys_form.api_key.non_empty'),
      requiredIf(sensitiveFieldEditable)
    )
  },
  apiSecret: {
    required: helpers.withMessage(
      t('exchange_keys_form.api_secret.non_empty'),
      requiredIf(logicAnd(sensitiveFieldEditable, requiresApiSecret))
    )
  },
  passphrase: {
    required: helpers.withMessage(
      t('exchange_keys_form.passphrase.non_empty'),
      requiredIf(logicAnd(sensitiveFieldEditable, requiresPassphrase))
    )
  }
};

const { valid, setValidation } = useExchangeApiKeysForm();

const v$ = setValidation(rules, exchange, { $autoDirty: true });
</script>

<template>
  <v-form ref="form" data-cy="exchange-keys" :value="valid">
    <v-row class="pt-2">
      <v-col cols="12" md="6">
        <v-autocomplete
          outlined
          :value="exchange.location"
          :items="exchanges"
          :label="t('exchange_keys_form.exchange')"
          data-cy="exchange"
          :disabled="editMode"
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
          v-if="editMode"
          outlined
          :value="exchange.newName"
          :error-messages="toMessages(v$.newName)"
          data-cy="name"
          :label="t('common.name')"
          @input="input({ ...exchange, newName: $event })"
        />
        <v-text-field
          v-else
          outlined
          :value="exchange.name"
          :error-messages="toMessages(v$.name)"
          data-cy="name"
          :label="t('common.name')"
          @input="input({ ...exchange, name: $event })"
        />
      </v-col>
    </v-row>

    <v-select
      v-if="exchange.location === 'kraken'"
      outlined
      :value="exchange.krakenAccountType"
      data-cy="account-type"
      :items="krakenAccountTypes"
      :label="t('exchange_settings.inputs.kraken_account')"
      @change="input({ ...exchange, krakenAccountType: $event })"
    />

    <div v-if="editMode" class="text-subtitle-2 mt-2 pb-4">
      {{ t('exchange_settings.keys') }}
      <v-tooltip top open-delay="400">
        <template #activator="{ on, attrs }">
          <v-btn
            icon
            v-bind="attrs"
            class="ml-4"
            v-on="on"
            @click="toggleEdit()"
          >
            <v-icon v-if="!editKeys">mdi-pencil-outline</v-icon>
            <v-icon v-else>mdi-close</v-icon>
          </v-btn>
        </template>
        <span>
          {{
            !editKeys
              ? t('exchange_keys_form.edit.activate_tooltip')
              : t('exchange_keys_form.edit.deactivate_tooltip')
          }}
        </span>
      </v-tooltip>
    </div>

    <div>
      <revealable-input
        outlined
        sensitive-key
        :disabled="editMode && !editKeys"
        :value="exchange.apiKey"
        :error-messages="toMessages(v$.apiKey)"
        data-cy="api-key"
        :label="t('exchange_settings.inputs.api_key')"
        @input="input({ ...exchange, apiKey: $event })"
        @paste="onApiKeyPaste($event)"
      />

      <revealable-input
        v-if="requiresApiSecret"
        outlined
        sensitive-key
        :disabled="editMode && !editKeys"
        :value="exchange.apiSecret"
        :error-messages="toMessages(v$.apiSecret)"
        data-cy="api-secret"
        prepend-icon="mdi-lock"
        :label="t('exchange_settings.inputs.api_secret')"
        @input="input({ ...exchange, apiSecret: $event })"
        @paste="onApiSecretPaste($event)"
      />

      <revealable-input
        v-if="requiresPassphrase"
        :disabled="editMode && !editKeys"
        outlined
        sensitive-key
        :value="exchange.passphrase"
        :error-messages="toMessages(v$.passphrase)"
        prepend-icon="mdi-key-plus"
        data-cy="passphrase"
        :label="t('exchange_settings.inputs.passphrase')"
        @input="input({ ...exchange, passphrase: $event })"
      />
    </div>

    <div v-if="exchange.location === 'ftx' || exchange.location === 'ftxus'">
      <v-text-field
        v-if="editMode"
        outlined
        :value="exchange.ftxSubaccount"
        data-cy="ftxSubaccount"
        :label="t('exchange_settings.inputs.ftx_subaccount')"
        @input="input({ ...exchange, ftxSubaccount: $event })"
      />
      <v-text-field
        v-else
        outlined
        :value="exchange.ftxSubaccount"
        data-cy="ftxSubaccount"
        :label="t('exchange_settings.inputs.ftx_subaccount')"
        @input="input({ ...exchange, ftxSubaccount: $event })"
      />
    </div>

    <binance-pairs-selector
      v-if="isBinance"
      outlined
      :name="exchange.name"
      :location="exchange.location"
      @input="input({ ...exchange, binanceMarkets: $event })"
    />
  </v-form>
</template>
