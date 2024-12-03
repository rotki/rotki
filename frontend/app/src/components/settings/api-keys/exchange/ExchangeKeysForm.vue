<script setup lang="ts">
import { helpers, requiredIf, requiredUnless } from '@vuelidate/validators';
import { type ExchangePayload, KrakenAccountType } from '@/types/exchanges';
import { toMessages } from '@/utils/validation';
import ExchangeKeysFormStructure from '@/components/settings/api-keys/exchange/ExchangeKeysFormStructure.vue';
import type { Writeable } from '@rotki/common';

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
    return props.modelValue.name ?? '';
  },
  set(value?: string) {
    updateModelValue({ ...props.modelValue, newName: value ?? null });
  },
});

const apiKey = computed({
  get() {
    return props.modelValue.apiKey ?? '';
  },
  set(value?: string) {
    updateModelValue({ ...props.modelValue, apiKey: value ?? null });
  },
});

const apiSecret = computed({
  get() {
    return props.modelValue.apiSecret ?? '';
  },
  set(value?: string) {
    updateModelValue({ ...props.modelValue, apiSecret: value ?? null });
  },
});

const passphrase = computed({
  get() {
    return props.modelValue.passphrase ?? '';
  },
  set(value?: string) {
    updateModelValue({ ...props.modelValue, passphrase: value ?? null });
  },
});

const krakenAccountType = computed<KrakenAccountType | undefined>({
  get() {
    return props.modelValue.krakenAccountType ?? undefined;
  },
  set(value?: KrakenAccountType) {
    updateModelValue({ ...props.modelValue, krakenAccountType: value ?? null });
  },
});

const { getExchangeNonce } = useExchangesStore();
const { exchangesWithPassphrase, exchangesWithoutApiSecret } = storeToRefs(useLocationStore());
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

const isKraken = computed(() => {
  const { location } = props.modelValue;
  return ['kraken'].includes(location);
});

const isCoinbase = computed(() => {
  const { location } = get(modelValue);
  return ['coinbase'].includes(location);
});

const isCoinbasePro = computed(() => {
  const { location } = get(modelValue);
  return ['coinbaseprime'].includes(location);
});

const showKeyWaitingTimeWarning = logicOr(isKraken, isCoinbase, isCoinbasePro);

const { getLocationData } = useLocations();

const suggestedName = function (exchange: string): string {
  const location = getLocationData(exchange);
  const nonce = get(getExchangeNonce(exchange));
  return location ? `${location.name} ${nonce}` : '';
};

function toggleEdit() {
  set(editKeys, !get(editKeys));

  if (!get(editKeys)) {
    updateModelValue({
      ...props.modelValue,
      apiSecret: null,
      apiKey: null,
    });
  }
}

function updateModelValue(payload: ExchangePayload) {
  const newPayload: Writeable<ExchangePayload> = {
    ...payload,
  };

  if (get(isCoinbase) && payload.apiSecret)
    newPayload.apiSecret = payload.apiSecret.replace(/\\n/g, '\n');

  emit('update:model-value', newPayload);
}

onMounted(() => {
  if (get(editMode))
    return;

  updateModelValue({
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

const sensitiveFieldEditable = computed(() => !get(editMode) || get(editKeys));

const rules = {
  name: {
    required: helpers.withMessage(t('exchange_keys_form.name.non_empty'), requiredUnless(editMode)),
  },
  newName: {
    required: helpers.withMessage(t('exchange_keys_form.name.non_empty'), requiredIf(editMode)),
  },
  apiKey: {
    required: helpers.withMessage(t('exchange_keys_form.validation.non_empty'), requiredIf(sensitiveFieldEditable)),
  },
  apiSecret: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(logicAnd(sensitiveFieldEditable, requiresApiSecret)),
    ),
  },
  passphrase: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(logicAnd(sensitiveFieldEditable, requiresPassphrase)),
    ),
  },
};

const { setValidation } = useExchangeApiKeysForm();

const v$ = setValidation(rules, modelValue, { $autoDirty: true });

function onExchangeChange(exchange?: string) {
  const name = exchange ?? '';
  updateModelValue({
    name: suggestedName(name),
    newName: null,
    location: name,
    apiKey: null,
    apiSecret: get(exchangesWithoutApiSecret).includes(name) ? '' : null,
    passphrase: null,
    krakenAccountType: name === 'kraken' ? 'starter' : null,
    binanceMarkets: null,
  });

  nextTick(() => {
    get(v$).$reset();
  });
}
</script>

<template>
  <div
    data-cy="exchange-keys"
    class="flex flex-col gap-4"
  >
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <ExchangeInput
        show-with-key-only
        :model-value="modelValue.location"
        :label="t('exchange_keys_form.exchange')"
        data-cy="exchange"
        :disabled="editMode"
        @update:model-value="onExchangeChange($event)"
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
        :model-value="modelValue.name"
        :error-messages="toMessages(v$.name)"
        data-cy="name"
        :label="t('common.name')"
        @update:model-value="updateModelValue({ ...modelValue, name: $event })"
      />
    </div>

    <RuiMenuSelect
      v-if="isKraken"
      v-model="krakenAccountType"
      data-cy="account-type"
      :options="krakenAccountTypes"
      :label="t('exchange_settings.inputs.kraken_account')"
      key-attr="identifier"
      text-attr="label"
      variant="outlined"
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
          !editKeys ? t('exchange_keys_form.edit.activate_tooltip') : t('exchange_keys_form.edit.deactivate_tooltip')
        }}
      </RuiTooltip>
    </div>

    <ExchangeKeysFormStructure :location="modelValue.location">
      <template #apiKey="{ label, hint, className }">
        <RuiRevealableTextField
          v-model.trim="apiKey"
          variant="outlined"
          color="primary"
          :disabled="editMode && !editKeys"
          :error-messages="toMessages(v$.apiKey)"
          data-cy="api-key"
          prepend-icon="key-line"
          :label="label"
          :hint="hint"
          :class="className"
        />
      </template>

      <template #apiSecret="{ label, hint, className }">
        <RuiRevealableTextField
          v-if="requiresApiSecret"
          v-model.trim="apiSecret"
          variant="outlined"
          color="primary"
          :disabled="editMode && !editKeys"
          :error-messages="toMessages(v$.apiSecret)"
          data-cy="api-secret"
          prepend-icon="lock-line"
          :label="label"
          :hint="hint"
          :class="className"
        />
      </template>

      <template #passphrase="{ label, hint, className }">
        <RuiRevealableTextField
          v-if="requiresPassphrase"
          v-model.trim="passphrase"
          :disabled="editMode && !editKeys"
          variant="outlined"
          color="primary"
          :error-messages="toMessages(v$.passphrase)"
          prepend-icon="key-line"
          data-cy="passphrase"
          :label="label"
          :hint="hint"
          :class="className"
        />
      </template>
    </ExchangeKeysFormStructure>

    <BinancePairsSelector
      v-if="isBinance"
      :name="modelValue.name"
      :location="modelValue.location"
      @update:selection="updateModelValue({ ...modelValue, binanceMarkets: $event })"
    />
  </div>

  <RuiAlert
    v-if="showKeyWaitingTimeWarning"
    class="mt-4"
    type="info"
  >
    {{ t('exchange_keys_form.waiting_time_warning') }}
  </RuiAlert>
</template>
