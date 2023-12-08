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

const name = computed({
  get() {
    return props.exchange.name ?? undefined;
  },
  set(value?: string) {
    input({ ...props.exchange, newName: value ?? null });
  }
});

const apiKey = computed({
  get() {
    return props.exchange.apiKey ?? undefined;
  },
  set(value?: string) {
    input({ ...props.exchange, apiKey: value ?? null });
  }
});

const apiSecret = computed({
  get() {
    return props.exchange.apiSecret ?? undefined;
  },
  set(value?: string) {
    input({ ...props.exchange, apiSecret: value ?? null });
  }
});

const passphrase = computed({
  get() {
    return props.exchange.passphrase ?? undefined;
  },
  set(value?: string) {
    input({ ...props.exchange, passphrase: value ?? null });
  }
});

const { getExchangeNonce } = useExchangesStore();
const { t, te } = useI18n();

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
  input({
    name: suggestedName(exchange),
    newName: null,
    location: exchange,
    apiKey: null,
    apiSecret: exchange === SupportedExchange.BITPANDA ? '' : null,
    passphrase: null,
    krakenAccountType: exchange === SupportedExchange.KRAKEN ? 'starter' : null,
    binanceMarkets: null
  });

  nextTick(() => {
    get(v$).$reset();
  });
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

const krakenAccountTypes = KrakenAccountType.options.map(item => {
  const translationKey = `backend_mappings.exchanges.kraken.type.${item}`;
  const label = te(translationKey) ? t(translationKey) : toSentenceCase(item);

  return {
    identifier: item,
    label
  };
});

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

const { setValidation } = useExchangeApiKeysForm();

const v$ = setValidation(rules, exchange, { $autoDirty: true });
</script>

<template>
  <div data-cy="exchange-keys" class="flex flex-col gap-2">
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <VAutocomplete
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
          <ExchangeDisplay
            :exchange="item"
            :class="`exchange__${item}`"
            v-bind="attrs"
            v-on="on"
          />
        </template>
        <template #item="{ item, attrs, on }">
          <ExchangeDisplay
            :exchange="item"
            :class="`exchange__${item}`"
            v-bind="attrs"
            v-on="on"
          />
        </template>
      </VAutocomplete>

      <RuiTextField
        v-if="editMode"
        v-model="name"
        variant="outlined"
        color="primary"
        :error-messages="toMessages(v$.newName)"
        data-cy="name"
        :label="t('common.name')"
      />

      <RuiTextField
        v-else
        variant="outlined"
        color="primary"
        :value="exchange.name"
        :error-messages="toMessages(v$.name)"
        data-cy="name"
        :label="t('common.name')"
        @input="input({ ...exchange, name: $event })"
      />
    </div>

    <VSelect
      v-if="exchange.location === 'kraken'"
      outlined
      :value="exchange.krakenAccountType"
      data-cy="account-type"
      :items="krakenAccountTypes"
      item-value="identifier"
      item-text="label"
      :label="t('exchange_settings.inputs.kraken_account')"
      @change="input({ ...exchange, krakenAccountType: $event })"
    />

    <div v-if="editMode" class="flex items-center gap-2 text-subtitle-2 pb-4">
      {{ t('exchange_settings.keys') }}
      <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
        <template #activator>
          <RuiButton variant="text" class="!p-2" icon @click="toggleEdit()">
            <RuiIcon
              size="20"
              :name="!editKeys ? 'pencil-line' : 'close-line'"
            />
          </RuiButton>
        </template>
        {{
          !editKeys
            ? t('exchange_keys_form.edit.activate_tooltip')
            : t('exchange_keys_form.edit.deactivate_tooltip')
        }}
      </RuiTooltip>
    </div>

    <RuiRevealableTextField
      v-model.trim="apiKey"
      variant="outlined"
      color="primary"
      :disabled="editMode && !editKeys"
      :error-messages="toMessages(v$.apiKey)"
      data-cy="api-key"
      :label="t('exchange_settings.inputs.api_key')"
    />

    <RuiRevealableTextField
      v-if="requiresApiSecret"
      v-model.trim="apiSecret"
      variant="outlined"
      color="primary"
      :disabled="editMode && !editKeys"
      :error-messages="toMessages(v$.apiSecret)"
      data-cy="api-secret"
      prepend-icon="lock-line"
      :label="t('exchange_settings.inputs.api_secret')"
    />

    <RuiRevealableTextField
      v-if="requiresPassphrase"
      v-model.trim="passphrase"
      :disabled="editMode && !editKeys"
      variant="outlined"
      color="primary"
      :error-messages="toMessages(v$.passphrase)"
      prepend-icon="key-line"
      data-cy="passphrase"
      :label="t('exchange_settings.inputs.passphrase')"
    />

    <BinancePairsSelector
      v-if="isBinance"
      outlined
      :name="exchange.name"
      :location="exchange.location"
      @input="input({ ...exchange, binanceMarkets: $event })"
    />
  </div>
</template>
