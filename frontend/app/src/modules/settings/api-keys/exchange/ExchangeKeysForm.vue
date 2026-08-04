<script setup lang="ts">
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { RuiRevealableTextField, RuiTextField } from '@rotki/ui-library';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf, requiredUnless } from '@vuelidate/validators';
import { type MessageKey, msg } from '@/message-key';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { type ExchangeFormData, GateLocation, KrakenAccountType, OkxLocation } from '@/modules/balances/types/exchanges';
import { useFormStateWatcher } from '@/modules/core/common/use-form';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import { refOptional, useRefPropVModel } from '@/modules/core/common/validation/model';
import { toMessages } from '@/modules/core/common/validation/validation';
import BinancePairsSelector from '@/modules/settings/api-keys/BinancePairsSelector.vue';
import BinanceHistoryStartDate from '@/modules/settings/api-keys/exchange/BinanceHistoryStartDate.vue';
import ExchangeKeysFormStructure from '@/modules/settings/api-keys/exchange/ExchangeKeysFormStructure.vue';
import GateRegionSelectorItem from '@/modules/settings/api-keys/exchange/GateRegionSelectorItem.vue';
import OkxRegionSelectorItem from '@/modules/settings/api-keys/exchange/OkxRegionSelectorItem.vue';
import ExchangeInput from '@/modules/shell/components/inputs/ExchangeInput.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';

const modelValue = defineModel<ExchangeFormData>({ required: true });

const stateUpdated = defineModel<boolean>('stateUpdated', { required: true });
const errorMessages = defineModel<ValidationErrors>('errorMessages', { default: () => ({}) });

const editKeys = ref<boolean>(false);
const editFuturesKeys = ref<boolean>(false);

const locationStore = useLocationStore();
const { exchangesWithoutApiSecret, exchangesWithPassphrase } = storeToRefs(locationStore);
const { useIsExperimentalExchange } = locationStore;
const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
const { getLocationData } = useLocations();
const { t } = useI18n({ useScope: 'global' });

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

const isGate = computed<boolean>(() => {
  const { location } = get(modelValue);
  return location === 'gate';
});

const isKraken = computed<boolean>(() => {
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

const experimental = useIsExperimentalExchange(() => get(modelValue).location);

const showKeyWaitingTimeWarning = logicOr(isKraken, isCoinbase, isCoinbasePro);

const historyLimitMessage = computed<string>(() => {
  const { location } = get(modelValue);
  if (location === 'bybit')
    return t('exchange_keys_form.history_limit_warning.bybit');
  if (location === 'htx')
    return t('exchange_keys_form.history_limit_warning.htx');
  if (location === 'cryptocom')
    return t('exchange_keys_form.history_limit_warning.cryptocom');
  return '';
});

const editMode = computed<boolean>(() => get(modelValue).mode === 'edit');
const showBinanceHistoryImport = computed<boolean>(() => (
  get(isBinance) && !get(editMode)
));

const nameProp = useRefPropVModel(modelValue, 'name');
const newNameProp = useRefPropVModel(modelValue, 'newName');
const apiKey = useRefPropVModel(modelValue, 'apiKey');
const apiSecret = useRefPropVModel(modelValue, 'apiSecret', {
  transform(value) {
    return get(isCoinbase) ? value.replace(/\\n/g, '\n') : value;
  },
});

const asteriskPlaceholder = '*'.repeat(30);

function createRefWithAsterisk(comp: WritableComputedRef<string>, editFlag: Ref<boolean>): WritableComputedRef<string> {
  return computed({
    get() {
      if (get(editMode) && !get(editFlag)) {
        return asteriskPlaceholder;
      }
      return get(comp);
    },
    set(value: string) {
      set(comp, value);
    },
  });
}

function createSensitiveInputComponent(editFlag: Ref<boolean>) {
  return computed(() => {
    if (!get(editMode) || get(editFlag)) {
      return RuiRevealableTextField;
    }
    return RuiTextField;
  });
}

const apiKeyModel = createRefWithAsterisk(apiKey, editKeys);
const apiSecretModel = createRefWithAsterisk(apiSecret, editKeys);
const sensitiveInputComponent = createSensitiveInputComponent(editKeys);

const passphrase = useRefPropVModel(modelValue, 'passphrase');
const krakenAccountType = useRefPropVModel(modelValue, 'krakenAccountType');
const krakenFuturesApiKey = useRefPropVModel(modelValue, 'krakenFuturesApiKey');
const krakenFuturesApiSecret = useRefPropVModel(modelValue, 'krakenFuturesApiSecret');
const binanceMarkets = useRefPropVModel(modelValue, 'binanceMarkets');
const binanceHistoryStartTs = useRefPropVModel(modelValue, 'binanceHistoryStartTs');
const gateLocation = useRefPropVModel(modelValue, 'gateLocation');
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

const krakenFuturesApiKeyComputed = refOptional(krakenFuturesApiKey, '');
const krakenFuturesApiSecretComputed = refOptional(krakenFuturesApiSecret, '');
const binanceHistoryStartTsModel = refOptional(
  binanceHistoryStartTs,
  Math.floor(Date.now() / 1000),
);

const krakenFuturesApiKeyModel = createRefWithAsterisk(krakenFuturesApiKeyComputed, editFuturesKeys);
const krakenFuturesApiSecretModel = createRefWithAsterisk(krakenFuturesApiSecretComputed, editFuturesKeys);
const futuresSensitiveInputComponent = createSensitiveInputComponent(editFuturesKeys);

useFormStateWatcher({
  apiKey,
  apiSecret,
  binanceHistoryStartTs,
  binanceMarkets,
  gateLocation,
  krakenAccountType,
  krakenFuturesApiKey,
  krakenFuturesApiSecret,
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

function toggleFuturesEdit() {
  set(editFuturesKeys, !get(editFuturesKeys));
  if (!get(editFuturesKeys)) {
    set(modelValue, {
      ...get(modelValue),
      krakenFuturesApiKey: '',
      krakenFuturesApiSecret: '',
    });
  }
}

// Exhaustive per option rather than an interpolated key, so adding an option fails typecheck here
// instead of silently falling back to the raw identifier, and so the keys are visible to the lint
// rules. Adding an option to any of these enums requires a matching message.
const GATE_LOCATION_KEYS: Record<GateLocation, MessageKey> = {
  europe: msg.$t('backend_mappings.exchanges.gate.location.europe'),
  global: msg.$t('backend_mappings.exchanges.gate.location.global'),
  us: msg.$t('backend_mappings.exchanges.gate.location.us'),
};

const KRAKEN_ACCOUNT_TYPE_KEYS: Record<KrakenAccountType, MessageKey> = {
  intermediate: msg.$t('backend_mappings.exchanges.kraken.type.intermediate'),
  pro: msg.$t('backend_mappings.exchanges.kraken.type.pro'),
  starter: msg.$t('backend_mappings.exchanges.kraken.type.starter'),
};

const OKX_LOCATION_KEYS: Record<OkxLocation, MessageKey> = {
  eea: msg.$t('backend_mappings.exchanges.okx.location.eea'),
  global: msg.$t('backend_mappings.exchanges.okx.location.global'),
  us: msg.$t('backend_mappings.exchanges.okx.location.us'),
};

const gateLocations = GateLocation.options.map(item => ({
  identifier: item,
  label: t(GATE_LOCATION_KEYS[item]),
}));

const krakenAccountTypes = KrakenAccountType.options.map(item => ({
  identifier: item,
  label: t(KRAKEN_ACCOUNT_TYPE_KEYS[item]),
}));

const okxLocations = OkxLocation.options.map(item => ({
  identifier: item,
  label: t(OKX_LOCATION_KEYS[item]),
}));

const sensitiveFieldEditable = logicOr(logicNot(editMode), editKeys);
const futuresFieldEditable = logicOr(logicNot(editMode), editFuturesKeys);
const hasFuturesApiKey = computed<boolean>(() => !!get(krakenFuturesApiKey));
const hasFuturesApiSecret = computed<boolean>(() => !!get(krakenFuturesApiSecret));

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
  krakenFuturesApiKey: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.futures_both_required'),
      requiredIf(logicAnd(futuresFieldEditable, hasFuturesApiSecret)),
    ),
  },
  krakenFuturesApiSecret: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.futures_both_required'),
      requiredIf(logicAnd(futuresFieldEditable, hasFuturesApiKey)),
    ),
  },
  binanceMarkets: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(isBinance),
    ),
  },
  binanceHistoryStartTs: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(showBinanceHistoryImport),
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
  gateLocation: {
    required: helpers.withMessage(
      t('exchange_keys_form.validation.non_empty'),
      requiredIf(isGate),
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
  binanceHistoryStartTs,
  krakenFuturesApiKey,
  krakenFuturesApiSecret,
  binanceMarkets,
  name: nameProp,
  newName: newNameProp,
  gateLocation,
  okxLocation,
  passphrase,
}, { $autoDirty: true, $externalResults: errorMessages });

function onExchangeChange(exchange?: string) {
  const name = exchange ?? '';
  const isKraken = name === 'kraken';

  set(modelValue, {
    apiKey: '',
    apiSecret: '',
    binanceHistoryStartTs: undefined,
    binanceMarkets: undefined,
    krakenAccountType: isKraken ? 'starter' : undefined,
    krakenFuturesApiKey: isKraken ? '' : undefined,
    gateLocation: name === 'gate' ? 'global' : undefined,
    krakenFuturesApiSecret: isKraken ? '' : undefined,
    location: name,
    mode: get(modelValue, 'mode'),
    name: suggestedName(name),
    newName: '',
    okxLocation: name === 'okx' ? 'global' : undefined,
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
        :label="t('common.exchange')"
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
      v-if="isGate"
      v-model="gateLocation"
      data-cy="gate-location"
      :options="gateLocations"
      :label="t('exchange_keys_form.region')"
      key-attr="identifier"
      text-attr="label"
      variant="outlined"
    >
      <template #selection="{ item }">
        <GateRegionSelectorItem
          :identifier="item.identifier"
          :label="item.label"
        />
      </template>
      <template #item="{ item }">
        <GateRegionSelectorItem
          :identifier="item.identifier"
          :label="item.label"
        />
      </template>
    </RuiMenuSelect>

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
        <Component
          :is="sensitiveInputComponent"
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
        <Component
          :is="sensitiveInputComponent"
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
        <Component
          :is="sensitiveInputComponent"
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

    <RuiAlert
      v-if="isBinance"
      data-testid="binance-warning"
      type="warning"
    >
      {{ t('exchange_keys_form.binance_markets_required') }}
      <div
        v-if="showBinanceHistoryImport"
        class="mt-2"
      >
        <i18n-t
          keypath="exchange_keys_form.binance_history_import.description"
          scope="global"
          tag="span"
        >
          <template #csvImport>
            <InternalLink
              :to="{
                name: '/import/',
                query: { source: 'binance' },
              }"
            >
              {{ t('exchange_keys_form.binance_history_import.link') }}
            </InternalLink>
          </template>
        </i18n-t>
        <BinanceHistoryStartDate
          v-model="binanceHistoryStartTsModel"
          :error-messages="toMessages(v$.binanceHistoryStartTs)"
        />
      </div>
    </RuiAlert>
    <template v-if="isKraken">
      <div
        class="flex items-center gap-2 text-subtitle-2 pb-4"
      >
        {{ t('exchange_settings.inputs.kraken_futures_keys') }}
        <RuiTooltip
          v-if="editMode"
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              variant="text"
              class="!p-2"
              icon
              @click="toggleFuturesEdit()"
            >
              <RuiIcon
                size="20"
                :name="!editFuturesKeys ? 'lu-pencil' : 'lu-x'"
              />
            </RuiButton>
          </template>
          {{
            !editFuturesKeys ? t('exchange_keys_form.edit.activate_tooltip') : t('exchange_keys_form.edit.deactivate_tooltip')
          }}
        </RuiTooltip>
      </div>
      <Component
        :is="futuresSensitiveInputComponent"
        v-model.trim="krakenFuturesApiKeyModel"
        variant="outlined"
        color="primary"
        :disabled="editMode && !editFuturesKeys"
        :error-messages="toMessages(v$.krakenFuturesApiKey)"
        data-cy="kraken-futures-api-key"
        prepend-icon="lu-key"
        :label="t('exchange_settings.inputs.futures_api_key')"
      />
      <Component
        :is="futuresSensitiveInputComponent"
        v-model.trim="krakenFuturesApiSecretModel"
        variant="outlined"
        color="primary"
        :disabled="editMode && !editFuturesKeys"
        :error-messages="toMessages(v$.krakenFuturesApiSecret)"
        data-cy="kraken-futures-api-secret"
        prepend-icon="lu-lock-keyhole"
        :label="t('exchange_settings.inputs.futures_api_secret')"
      />
    </template>

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
    v-if="showKeyWaitingTimeWarning"
    class="mt-4"
    type="info"
  >
    {{ t('exchange_keys_form.waiting_time_warning') }}
  </RuiAlert>

  <RuiAlert
    v-if="historyLimitMessage"
    class="mt-4"
    type="warning"
  >
    {{ historyLimitMessage }}
  </RuiAlert>

  <RuiAlert
    v-if="experimental"
    type="info"
    class="mt-4"
  >
    {{ t('exchange_settings.inputs.experimental') }}
  </RuiAlert>
</template>
