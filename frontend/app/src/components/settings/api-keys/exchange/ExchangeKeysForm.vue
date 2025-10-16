<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import { toSentenceCase } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf, requiredUnless } from '@vuelidate/validators';
import BinancePairsSelector from '@/components/helper/BinancePairsSelector.vue';
import ExchangeInput from '@/components/inputs/ExchangeInput.vue';
import ExchangeKeysFormStructure from '@/components/settings/api-keys/exchange/ExchangeKeysFormStructure.vue';
import OkxRegionSelectorItem from '@/components/settings/api-keys/exchange/OkxRegionSelectorItem.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useLocations } from '@/composables/locations';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useLocationStore } from '@/store/locations';
import { useSessionSettingsStore } from '@/store/settings/session';
import { type ExchangeFormData, KrakenAccountType, OkxLocation } from '@/types/exchanges';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<ExchangeFormData>({ required: true });

const stateUpdated = defineModel<boolean>('stateUpdated', { required: true });
const errorMessages = defineModel<ValidationErrors>('errorMessages', { default: () => ({}) });

const editKeys = ref<boolean>(false);

const locationStore = useLocationStore();
const { exchangesWithoutApiSecret, exchangesWithPassphrase } = storeToRefs(locationStore);
const { useIsExperimentalExchange } = locationStore;
const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const { getLocationData } = useLocations();
const { t, te } = useI18n({ useScope: 'global' });

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

const isKraken = computed(() => {
  const { location } = get(modelValue);
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

const isOkx = computed(() => {
  const { location } = get(modelValue);
  return ['okx'].includes(location);
});

const location = useRefMap(modelValue, item => item.location);
const experimental = useIsExperimentalExchange(location);

const showKeyWaitingTimeWarning = logicOr(isKraken, isCoinbase, isCoinbasePro);

const editMode = computed<boolean>(() => get(modelValue).mode === 'edit');

const nameProp = useRefPropVModel(modelValue, 'name');
const newNameProp = useRefPropVModel(modelValue, 'newName');
const apiKey = useRefPropVModel(modelValue, 'apiKey');
const apiSecret = useRefPropVModel(modelValue, 'apiSecret', {
  transform(value) {
    return get(isCoinbase) ? value.replace(/\\n/g, '\n') : value;
  },
});

const asteriskPlaceholder = '*'.repeat(30);

function refWithAsterisk(comp: WritableComputedRef<string>): WritableComputedRef<string> {
  return computed({
    get() {
      if (get(editMode) && !get(editKeys)) {
        return asteriskPlaceholder;
      }
      return get(comp);
    },
    set(value: string) {
      set(comp, value);
    },
  });
}

const apiKeyModel = refWithAsterisk(apiKey);
const apiSecretModel = refWithAsterisk(apiSecret);

const passphrase = useRefPropVModel(modelValue, 'passphrase');
const krakenAccountType = useRefPropVModel(modelValue, 'krakenAccountType');
const binanceMarkets = useRefPropVModel(modelValue, 'binanceMarkets');
const okxLocation = useRefPropVModel(modelValue, 'okxLocation');

const name = computed<string>({
  get() {
    return get(editMode) ? (get(newNameProp) || '') : get(nameProp);
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
  apiKey,
  apiSecret,
  binanceMarkets,
  krakenAccountType,
  name,
  okxLocation,
  passphrase,
}, stateUpdated);

function suggestedName(exchange: string): string {
  const location = getLocationData(exchange);
  const nonce = get(connectedExchanges).filter(({ location }) => location === exchange).length + 1;
  return location ? `${location.name} ${nonce}` : '';
}

function toggleEdit() {
  set(editKeys, !get(editKeys));

  if (!get(editKeys)) {
    set(modelValue, {
      ...get(modelValue),
      apiKey: '',
      apiSecret: '',
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

const okxLocations = OkxLocation.options.map((item) => {
  const translationKey = `backend_mappings.exchanges.okx.location.${item.toLowerCase()}`;
  const label = te(translationKey) ? t(translationKey) : item;

  return {
    identifier: item,
    label,
  };
});

const sensitiveFieldEditable = logicOr(logicNot(editMode), editKeys);

const v$ = useVuelidate({
  apiKey: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(sensitiveFieldEditable),
    ),
  },
  apiSecret: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(logicAnd(sensitiveFieldEditable, requiresApiSecret)),
    ),
  },
  binanceMarkets: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(isBinance),
    ),
  },
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
  okxLocation: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(isOkx),
    ),
  },
  passphrase: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(logicAnd(sensitiveFieldEditable, requiresPassphrase)),
    ),
  },
}, {
  apiKey,
  apiSecret,
  binanceMarkets,
  name: nameProp,
  newName: newNameProp,
  okxLocation,
  passphrase,
}, { $autoDirty: true, $externalResults: errorMessages });

function onExchangeChange(exchange?: string) {
  const name = exchange ?? '';
  set(modelValue, {
    apiKey: '',
    apiSecret: '',
    binanceMarkets: undefined,
    krakenAccountType: name === 'kraken' ? 'starter' : undefined,
    location: name,
    mode: get(modelValue, 'mode'),
    name: suggestedName(name),
    newName: '',
    okxLocation: name === 'okx' ? 'GLOBAL' : undefined,
    passphrase: '',
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
      v-if="isKraken"
      v-model="krakenAccountType"
      data-cy="account-type"
      :options="krakenAccountTypes"
      :label="t('exchange_settings.inputs.kraken_account')"
      key-attr="identifier"
      text-attr="label"
      variant="outlined"
    />

    <RuiMenuSelect
      v-if="isOkx"
      v-model="okxLocation"
      data-cy="okx-location"
      :options="okxLocations"
      :label="t('exchange_keys_form.region')"
      key-attr="identifier"
      text-attr="label"
      variant="outlined"
    >
      <template #selection="{ item }">
        <OkxRegionSelectorItem
          :identifier="item.identifier"
          :label="item.label"
        />
      </template>
      <template #item="{ item }">
        <OkxRegionSelectorItem
          :identifier="item.identifier"
          :label="item.label"
        />
      </template>
    </RuiMenuSelect>

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
              :name="!editKeys ? 'lu-pencil' : 'lu-x'"
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
          v-model.trim="apiKeyModel"
          :text-color="editMode && !editKeys && toMessages(v$.apiKey).length === 0 ? 'success' : undefined"
          variant="outlined"
          color="primary"
          :disabled="editMode && !editKeys"
          :error-messages="toMessages(v$.apiKey)"
          data-cy="api-key"
          prepend-icon="lu-key"
          :label="label"
          :hint="hint"
          :class="className"
        />
      </template>

      <template #apiSecret="{ label, hint, className }">
        <RuiRevealableTextField
          v-if="requiresApiSecret"
          v-model.trim="apiSecretModel"
          variant="outlined"
          color="primary"
          :text-color="editMode && !editKeys && toMessages(v$.apiKey).length === 0 ? 'success' : undefined"
          :disabled="editMode && !editKeys"
          :error-messages="toMessages(v$.apiSecret)"
          data-cy="api-secret"
          prepend-icon="lu-lock-keyhole"
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
          prepend-icon="lu-key"
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
      :edit="editMode"
      :location="modelValue.location"
      :error-messages="toMessages(v$.binanceMarkets)"
      @update:selection="modelValue = { ...modelValue, binanceMarkets: $event }"
    />
  </div>

  <RuiAlert
    v-if="isBinance"
    class="mt-4"
    type="info"
  >
    {{ t('exchange_keys_form.binance_markets_required') }}
  </RuiAlert>

  <RuiAlert
    v-if="showKeyWaitingTimeWarning"
    class="mt-4"
    type="info"
  >
    {{ t('exchange_keys_form.waiting_time_warning') }}
  </RuiAlert>

  <RuiAlert
    v-if="experimental"
    type="info"
    class="mt-4"
  >
    {{ t('exchange_settings.inputs.experimental') }}
  </RuiAlert>
</template>
