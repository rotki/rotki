<script setup lang="ts">
import { helpers, requiredIf, requiredUnless } from '@vuelidate/validators';
import { type ExchangePayload, KrakenAccountType } from '@/types/exchanges';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  modelValue: ExchangePayload;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: ExchangePayload): void;
}>();

const { editMode, modelValue } = toRefs(props);
const editKeys = ref(false);

const name = computed({
  get() {
    return props.modelValue.name ?? undefined;
  },
  set(value?: string) {
    input({ ...props.modelValue, newName: value ?? null });
  },
});

const apiKey = computed({
  get() {
    return props.modelValue.apiKey ?? undefined;
  },
  set(value?: string) {
    input({ ...props.modelValue, apiKey: value ?? null });
  },
});

const apiSecret = computed({
  get() {
    return props.modelValue.apiSecret ?? undefined;
  },
  set(value?: string) {
    input({ ...props.modelValue, apiSecret: value ?? null });
  },
});

const passphrase = computed({
  get() {
    return props.modelValue.passphrase ?? undefined;
  },
  set(value?: string) {
    input({ ...props.modelValue, passphrase: value ?? null });
  },
});

const { getExchangeNonce } = useExchangesStore();
const { t, te } = useI18n();

const requiresApiSecret = computed(() => {
  const { location } = props.modelValue;

  return !get(exchangesWithoutApiSecret).includes(location);
});

const requiresPassphrase = computed(() => {
  const { location } = props.modelValue;
  return get(exchangesWithPassphrase).includes(location);
});

const isBinance = computed(() => {
  const { location } = props.modelValue;
  return ['binance', 'binanceus'].includes(location);
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
      ...props.modelValue,
      apiSecret: null,
      apiKey: null,
    });
  }
}

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

function input(payload: ExchangePayload) {
  emit('update:model-value', payload);
}

onMounted(() => {
  if (get(editMode))
    return;

  input({
    ...props.modelValue,
    name: suggestedName(props.modelValue.location),
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

const { exchangesWithKey, exchangesWithPassphrase, exchangesWithoutApiSecret }
  = storeToRefs(useLocationStore());

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

const v$ = setValidation(rules, modelValue, { $autoDirty: true });
</script>

<template>
  <div
    data-cy="exchange-keys"
    class="flex flex-col gap-2"
  >
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <VAutocomplete
        variant="outlined"
        :model-value="modelValue.location"
        :items="exchangesWithKey"
        :label="t('exchange_keys_form.exchange')"
        data-cy="exchange"
        :disabled="editMode"
        auto-select-first
        @update:model-value="onExchangeChange($event)"
      >
        <template #selection="{ item }">
          <ExchangeDisplay
            :exchange="item.raw"
            :class="`exchange__${item.raw}`"
          />
        </template>
        <template #item="{ item, props }">
          <ExchangeDisplay
            :exchange="item.raw"
            :class="`exchange__${item}`"
            v-bind="props"
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
        :value="modelValue.name"
        :error-messages="toMessages(v$.name)"
        data-cy="name"
        :label="t('common.name')"
        @input="input({ ...modelValue, name: $event })"
      />
    </div>

    <VSelect
      v-if="modelValue.location === 'kraken'"
      variant="outlined"
      :model-value="modelValue.krakenAccountType"
      data-cy="account-type"
      :items="krakenAccountTypes"
      item-value="identifier"
      item-title="label"
      :label="t('exchange_settings.inputs.kraken_account')"
      @update:model-value="input({ ...modelValue, krakenAccountType: $event })"
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
      :name="modelValue.name"
      :location="modelValue.location"
      @update:selection="input({ ...modelValue, binanceMarkets: $event })"
    />
  </div>
</template>
