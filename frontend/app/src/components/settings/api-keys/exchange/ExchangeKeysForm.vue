<script setup lang="ts">
import { helpers, requiredIf, requiredUnless } from '@vuelidate/validators';
import { type ExchangePayload, KrakenAccountType } from '@/types/exchanges';
import { toMessages } from '@/utils/validation';
import type { Writeable } from '@/types';

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
  },
});

const apiKey = computed({
  get() {
    return props.exchange.apiKey ?? undefined;
  },
  set(value?: string) {
    input({ ...props.exchange, apiKey: value ?? null });
  },
});

const apiSecret = computed({
  get() {
    return props.exchange.apiSecret ?? undefined;
  },
  set(value?: string) {
    input({ ...props.exchange, apiSecret: value ?? null });
  },
});

const passphrase = computed({
  get() {
    return props.exchange.passphrase ?? undefined;
  },
  set(value?: string) {
    input({ ...props.exchange, passphrase: value ?? null });
  },
});

const { getExchangeNonce } = useExchangesStore();
const { exchangesWithPassphrase, exchangesWithoutApiSecret } = storeToRefs(useLocationStore());
const { t, te } = useI18n();

const requiresApiSecret = computed(() => {
  const { location } = get(exchange);

  return !get(exchangesWithoutApiSecret).includes(location);
});

const requiresPassphrase = computed(() => {
  const { location } = get(exchange);
  return get(exchangesWithPassphrase).includes(location);
});

const isBinance = computed(() => {
  const { location } = get(exchange);
  return ['binance', 'binanceus'].includes(location);
});

const isCoinbase = computed(() => {
  const { location } = get(exchange);
  return ['coinbase'].includes(location);
});

const { getLocationData } = useLocations();

const suggestedName = function (exchange: string): string {
  const location = getLocationData(exchange);
  const nonce = get(getExchangeNonce(exchange));
  return location ? `${location.name} ${nonce}` : '';
};

function toggleEdit() {
  set(editKeys, !get(editKeys));

  if (!get(editKeys)) {
    input({
      ...get(exchange),
      apiSecret: null,
      apiKey: null,
    });
  }
}

function input(payload: ExchangePayload) {
  const newPayload: Writeable<ExchangePayload> = {
    ...payload,
  };

  if (get(isCoinbase) && payload.apiSecret)
    newPayload.apiSecret = payload.apiSecret.replace(/\\n/g, '\n');

  emit('input', newPayload);
}

onMounted(() => {
  if (get(editMode))
    return;

  input({
    ...get(exchange),
    name: suggestedName(get(exchange).location),
  });
});

const krakenAccountTypes = KrakenAccountType.options.map((item) => {
  const translationKey = `backend_mappings.exchanges.kraken.type.${item}`;
  const label = te(translationKey) ? t(translationKey) : toSentenceCase(item);

  return {
    identifier: item,
    label,
  };
});

const sensitiveFieldEditable = computed(() => !get(editMode) || get(editKeys));

const rules = {
  name: {
    required: helpers.withMessage(
      t('exchange_keys_form.name.non_empty'),
      requiredUnless(editMode),
    ),
  },
  newName: {
    required: helpers.withMessage(
      t('exchange_keys_form.name.non_empty'),
      requiredIf(editMode),
    ),
  },
  apiKey: {
    required: helpers.withMessage(
      t('exchange_keys_form.api_key.non_empty'),
      requiredIf(sensitiveFieldEditable),
    ),
  },
  apiSecret: {
    required: helpers.withMessage(
      t('exchange_keys_form.api_secret.non_empty'),
      requiredIf(logicAnd(sensitiveFieldEditable, requiresApiSecret)),
    ),
  },
  passphrase: {
    required: helpers.withMessage(
      t('exchange_keys_form.passphrase.non_empty'),
      requiredIf(logicAnd(sensitiveFieldEditable, requiresPassphrase)),
    ),
  },
};

const { setValidation } = useExchangeApiKeysForm();

const v$ = setValidation(rules, exchange, { $autoDirty: true });

function onExchangeChange(exchange: string) {
  input({
    name: suggestedName(exchange),
    newName: null,
    location: exchange,
    apiKey: null,
    apiSecret: get(exchangesWithoutApiSecret).includes(exchange) ? '' : null,
    passphrase: null,
    krakenAccountType: exchange === 'kraken' ? 'starter' : null,
    binanceMarkets: null,
  });

  nextTick(() => {
    get(v$).$reset();
  });
}

const coinbaseApiKeyNameFormat = 'organizations/{org_id}/apiKeys/{key_id}';
const coinbasePrivateKeyFormat = '-----BEGIN EC PRIVATE KEY-----\\n{KEY}\\n-----END EC PRIVATE KEY-----\\n';
</script>

<template>
  <div
    data-cy="exchange-keys"
    class="flex flex-col gap-4"
  >
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <ExchangeInput
        show-with-key-only
        :value="exchange.location"
        :label="t('exchange_keys_form.exchange')"
        data-cy="exchange"
        :disabled="editMode"
        @input="onExchangeChange($event)"
      />

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

    <RuiMenuSelect
      v-if="exchange.location === 'kraken'"
      :value="exchange.krakenAccountType"
      data-cy="account-type"
      :options="krakenAccountTypes"
      :label="t('exchange_settings.inputs.kraken_account')"
      key-attr="identifier"
      text-attr="label"
      full-width
      show-details
      variant="outlined"
      @input="input({ ...exchange, krakenAccountType: $event })"
    />

    <div
      v-if="editMode"
      class="flex items-center gap-2 text-subtitle-2 pb-4"
    >
      {{ t('exchange_settings.keys') }}
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            class="!p-2"
            icon
            @click="toggleEdit()"
          >
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
      prepend-icon="key-line"
      :label="isCoinbase ? t('exchange_settings.inputs.api_key_name') : t('exchange_settings.inputs.api_key')"
      :hint="isCoinbase ? `${t('exchange_settings.inputs.format')}: ${coinbaseApiKeyNameFormat}` : ''"
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
      :label="isCoinbase ? t('exchange_settings.inputs.private_key') : t('exchange_settings.inputs.api_secret')"
      :hint="isCoinbase ? `${t('exchange_settings.inputs.format')}: ${coinbasePrivateKeyFormat}` : ''"
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
