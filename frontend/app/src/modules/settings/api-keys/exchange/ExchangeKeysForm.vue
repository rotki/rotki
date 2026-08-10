<script setup lang="ts">
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { RuiRevealableTextField, RuiTextField } from '@rotki/ui-library';
import { type MessageKey, msg } from '@/message-key';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { type ExchangeFormData, GateLocation, KrakenAccountType, OkxLocation } from '@/modules/balances/types/exchanges';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import { refOptional, useRefPropVModel } from '@/modules/core/common/validation/model';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { useForm } from '@/modules/core/form/use-form';
import BinancePairsSelector from '@/modules/settings/api-keys/BinancePairsSelector.vue';
import BinanceHistoryStartDate from '@/modules/settings/api-keys/exchange/BinanceHistoryStartDate.vue';
import {
  isBinance as binance,
  type ExchangeCapabilities,
  type ExchangeKeysFormState,
  exchangeKeysSchema,
  isGate as gate,
  isEditing,
  isKraken as kraken,
  requiresApiSecret as needsApiSecret,
  requiresPassphrase as needsPassphrase,
  normalizeApiSecret,
  isOkx as okx,
  showsBinanceHistoryImport,
  toExchangeKeysFormState,
} from '@/modules/settings/api-keys/exchange/exchange-keys-form';
import ExchangeKeysFormStructure from '@/modules/settings/api-keys/exchange/ExchangeKeysFormStructure.vue';
import ExchangeNotices from '@/modules/settings/api-keys/exchange/ExchangeNotices.vue';
import GateRegionSelectorItem from '@/modules/settings/api-keys/exchange/GateRegionSelectorItem.vue';
import KrakenFuturesKeys from '@/modules/settings/api-keys/exchange/KrakenFuturesKeys.vue';
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

const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
const { getLocationData } = useLocations();
const { t } = useI18n({ useScope: 'global' });

const capabilities = computed<ExchangeCapabilities>(() => ({
  withoutApiSecret: get(exchangesWithoutApiSecret),
  withPassphrase: get(exchangesWithPassphrase),
}));

const location = computed<string>(() => get(modelValue).location);

const requiresApiSecret = computed<boolean>(() => needsApiSecret(get(location), get(capabilities)));
const requiresPassphrase = computed<boolean>(() => needsPassphrase(get(location), get(capabilities)));
const isBinance = computed<boolean>(() => binance(get(location)));
const isGate = computed<boolean>(() => gate(get(location)));
const isKraken = computed<boolean>(() => kraken(get(location)));
const isOkx = computed<boolean>(() => okx(get(location)));

const editMode = computed<boolean>(() => isEditing(get(modelValue).mode));
const showBinanceHistoryImport = computed<boolean>(() => {
  const { location, mode } = get(modelValue);
  return showsBinanceHistoryImport(location, mode);
});

const nameProp = useRefPropVModel(modelValue, 'name');
const newNameProp = useRefPropVModel(modelValue, 'newName');
const apiKey = useRefPropVModel(modelValue, 'apiKey');
const apiSecret = useRefPropVModel(modelValue, 'apiSecret', {
  transform(value) {
    return normalizeApiSecret(get(location), value);
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

const binanceHistoryStartTsModel = refOptional(
  binanceHistoryStartTs,
  Math.floor(Date.now() / 1000),
);

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

/**
 * The dialog owns the entry, so the form mirrors it rather than holding its own copy: the fields
 * keep writing where they always did, and the rules always read what is on screen.
 */
const form = useForm<ExchangeKeysFormState, ExchangeKeysFormState>({
  initial: (): ExchangeKeysFormState => toExchangeKeysFormState(get(modelValue)),
  schema: computed(() => exchangeKeysSchema({
    capabilities: get(capabilities),
    editingFutures: get(editFuturesKeys),
    editingKeys: get(editKeys),
    location: get(location),
    mode: get(modelValue).mode,
  })),
  // The dialog persists; there is nothing to submit from here.
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): ExchangeKeysFormState => ({ ...state }),
});

watchDeep(modelValue, (value) => {
  Object.assign(form.state, toExchangeKeysFormState(value));
});

watch(errorMessages, (value) => {
  form.setServerErrors(toServerErrors(value));
}, { deep: true, immediate: true });

watch(form.dirty, (dirty) => {
  set(stateUpdated, dirty);
});

// The dialog keeps its prompt-on-close flag across opens, so hand it back disarmed.
onUnmounted(() => {
  set(stateUpdated, false);
});

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

  // Picking a different exchange starts a different connection, so the errors from the last one
  // must not be left decorating the new form.
  nextTick(() => {
    form.reset(toExchangeKeysFormState(get(modelValue)));
  });
}

function seedName(): void {
  if (get(editMode)) {
    set(newNameProp, get(nameProp));
    return;
  }

  const model = get(modelValue);
  // The locations come from the backend, so the store holds none until that fetch lands and the
  // suggestion comes back empty. This runs once, so writing that over the name would leave the
  // field blank with nothing left to restore it.
  const suggestion = suggestedName(model.location);
  if (!suggestion)
    return;

  set(modelValue, {
    ...model,
    name: suggestion,
  });
}

onMounted(() => {
  seedName();
  // The seeded name lands after `useForm` took its baseline, so take it again. Otherwise a dialog
  // the user has not touched counts as dirty and prompts to discard on close. This has to run in
  // the same tick as the seeding: a deferred reset lets `dirty` flip on the way, and the dialog
  // latches the flag it is handed.
  form.reset(toExchangeKeysFormState(get(modelValue)));
});

defineExpose({
  validate: (): boolean => form.validate(),
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
        :error-messages="editMode ? form.errors('newName') : form.errors('name')"
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
            data-cy="toggle-edit-keys"
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
          :text-color="editMode && !editKeys && form.errors('apiKey').length === 0 ? 'success' : undefined"
          variant="outlined"
          color="primary"
          :disabled="editMode && !editKeys"
          :error-messages="form.errors('apiKey')"
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
          :text-color="editMode && !editKeys && form.errors('apiKey').length === 0 ? 'success' : undefined"
          :disabled="editMode && !editKeys"
          :error-messages="form.errors('apiSecret')"
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
          :error-messages="form.errors('passphrase')"
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
          :error-messages="form.errors('binanceHistoryStartTs')"
        />
      </div>
    </RuiAlert>
    <KrakenFuturesKeys
      v-if="isKraken"
      v-model:api-key="krakenFuturesApiKey"
      v-model:api-secret="krakenFuturesApiSecret"
      v-model:editing="editFuturesKeys"
      :edit-mode="editMode"
      :key-errors="form.errors('krakenFuturesApiKey')"
      :secret-errors="form.errors('krakenFuturesApiSecret')"
    />
    <BinancePairsSelector
      v-if="isBinance"
      :name="modelValue.name"
      :edit="editMode"
      :location="modelValue.location"
      :error-messages="form.errors('binanceMarkets')"
      @update:selection="modelValue = { ...modelValue, binanceMarkets: $event }"
    />
  </div>

  <ExchangeNotices :location="modelValue.location" />
</template>
