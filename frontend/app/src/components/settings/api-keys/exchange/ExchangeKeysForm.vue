<script setup lang="ts">
import { helpers, requiredIf, requiredUnless } from '@vuelidate/validators';
import useVuelidate from '@vuelidate/core';
import { type ExchangeFormData, KrakenAccountType } from '@/types/exchanges';
import { toMessages } from '@/utils/validation';
import { useRefPropVModel } from '@/utils/model';

const modelValue = defineModel<ExchangeFormData>({ required: true });

const stateUpdated = defineModel<boolean>('stateUpdated', { required: true });

const editKeys = ref<boolean>(false);

const coinbaseApiKeyNameFormat = 'organizations/{org_id}/apiKeys/{key_id}';
const coinbasePrivateKeyFormat = '-----BEGIN EC PRIVATE KEY-----\\n{KEY}\\n-----END EC PRIVATE KEY-----\\n';

const { getExchangeNonce } = useExchangesStore();
const { exchangesWithPassphrase, exchangesWithoutApiSecret } = storeToRefs(useLocationStore());
const { getLocationData } = useLocations();
const { t, te } = useI18n();

const requiresApiSecret = computed(() => {
  const { location } = get(modelValue);
  return !get(exchangesWithoutApiSecret).includes(location);
});

const requiresPassphrase = computed(() => {
  const { location } = get(modelValue);
  return get(exchangesWithPassphrase).includes(location);
});

const isBinance = computed(() => {
  const { location } = get(modelValue);
  return ['binance', 'binanceus'].includes(location);
});

const isCoinbase = computed(() => {
  const { location } = get(modelValue);
  return ['coinbase'].includes(location);
});

const editMode = computed<boolean>(() => get(modelValue).mode === 'edit');

const nameProp = useRefPropVModel(modelValue, 'name');
const newNameProp = useRefPropVModel(modelValue, 'newName');
const apiKey = useRefPropVModel(modelValue, 'apiKey');
const apiSecret = useRefPropVModel(modelValue, 'apiSecret', {
  transform(value) {
    return get(isCoinbase) ? value.replace(/\\n/g, '\n') : value;
  },
});
const passphrase = useRefPropVModel(modelValue, 'passphrase');
const krakenAccountType = useRefPropVModel(modelValue, 'krakenAccountType');

const name = computed<string>({
  get() {
    return get(editMode) ? get(newNameProp) : get(nameProp);
  },
  set(value?: string) {
    if (get(editMode)) {
      set(newNameProp, value);
    }
    else {
      set(nameProp, value);
    }
  },
});

useFormStateWatcher({
  name,
  apiKey,
  apiSecret,
  passphrase,
  krakenAccountType,
}, stateUpdated);

const suggestedName = function (exchange: string): string {
  const location = getLocationData(exchange);
  const nonce = get(getExchangeNonce(exchange));
  return location ? `${location.name} ${nonce}` : '';
};

function toggleEdit() {
  set(editKeys, !get(editKeys));

  if (!get(editKeys)) {
    set(modelValue, {
      ...get(modelValue),
      apiSecret: '',
      apiKey: '',
    });
  }
}

const krakenAccountTypes = KrakenAccountType.options.map((item) => {
  const translationKey = `backend_mappings.exchanges.kraken.type.${item}`;
  const label = te(translationKey) ? t(translationKey) : toSentenceCase(item);

  return {
    identifier: item,
    label,
  };
});

const sensitiveFieldEditable = logicOr(logicNot(editMode), editKeys);

const v$ = useVuelidate({
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
}, modelValue, { $autoDirty: true });

function onExchangeChange(exchange?: string) {
  const name = exchange ?? '';
  set(modelValue, {
    mode: get(modelValue, 'mode'),
    name: suggestedName(name),
    newName: '',
    location: name,
    apiKey: '',
    apiSecret: '',
    passphrase: '',
    krakenAccountType: name === 'kraken' ? 'starter' : undefined,
    binanceMarkets: undefined,
  });

  nextTick(() => {
    get(v$).$reset();
  });
}

onMounted(() => {
  if (get(editMode)) {
    set(newNameProp, get(nameProp));
    return;
  }

  const model = get(modelValue);
  set(modelValue, {
    ...model,
    name: suggestedName(model.location),
  });
});

defineExpose({
  validate: async (): Promise<boolean> => await get(v$).$validate(),
});
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
        v-model="name"
        variant="outlined"
        color="primary"
        :error-messages="editMode ? toMessages(v$.newName) : toMessages(v$.name)"
        data-cy="name"
        :label="t('common.name')"
      />
    </div>

    <RuiMenuSelect
      v-if="modelValue.location === 'kraken'"
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
      :name="modelValue.name"
      :location="modelValue.location"
      @update:selection="modelValue = { ...modelValue, binanceMarkets: $event }"
    />
  </div>
</template>
