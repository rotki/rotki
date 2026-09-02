<script setup lang="ts">
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { RuiRevealableTextField, RuiTextField } from '@rotki/ui-library';
import { type MessageKey, msg } from '@/message-key';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { type ExchangeFormData, GateLocation, KrakenAccountType, OkxLocation } from '@/modules/balances/types/exchanges';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import { useMappedModelForm } from '@/modules/core/form/use-model-form';
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

/**
 * The dialog owns the entry, so the form mirrors it: the inputs write `form.state`, and every edit
 * is folded back over the entry the dialog is about to save.
 */
const form = useMappedModelForm<ExchangeFormData, ExchangeKeysFormState>({
  model: modelValue,
  schema: computed(() => exchangeKeysSchema({
    capabilities: get(capabilities),
    editingFutures: get(editFuturesKeys),
    editingKeys: get(editKeys),
    location: get(location),
    mode: get(modelValue).mode,
  })),
  serverErrors: errorMessages,
  stateUpdated,
  toModel: (state, entry): ExchangeFormData => ({ ...entry, ...state }),
  toState: toExchangeKeysFormState,
});

/**
 * The secret, normalised as it is typed.
 *
 * @remarks
 * Coinbase hands out a secret containing a literal `\n`. Normalising on write rather than on the way
 * to the entry means the field shows what will actually be sent, instead of appearing to correct
 * itself a tick after the paste.
 */
const apiSecret = computed<string>({
  get: () => form.state.apiSecret,
  set: (value: string) => {
    form.state.apiSecret = normalizeApiSecret(get(location), value);
  },
});

const asteriskPlaceholder = '*'.repeat(30);

function createRefWithAsterisk(
  comp: Ref<string> | WritableComputedRef<string>,
  editFlag: Ref<boolean>,
): WritableComputedRef<string> {
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

const apiKeyModel = createRefWithAsterisk(toRef(form.state, 'apiKey'), editKeys);
const apiSecretModel = createRefWithAsterisk(apiSecret, editKeys);
const sensitiveInputComponent = createSensitiveInputComponent(editKeys);

/**
 * The connection's name, which an edit writes to a second field so that the name it is currently
 * stored under stays readable while the new one is being typed.
 */
const name = computed<string>({
  get() {
    return get(editMode) ? (form.state.newName ?? '') : form.state.name;
  },
  set(value: string) {
    if (get(editMode)) {
      form.state.newName = value;
    }
    else {
      form.state.name = value;
    }
  },
});

/**
 * Where the history picker opens for an entry with no start date yet, in seconds.
 *
 * @remarks
 * Captured once at setup rather than read per call. A default that moved on every read would make
 * the form look as though it had edited itself.
 */
const defaultHistoryStart = Math.floor(Date.now() / 1000);

const binanceHistoryStartTsModel = computed<number>({
  get: () => form.state.binanceHistoryStartTs ?? defaultHistoryStart,
  set: (value: number) => {
    form.state.binanceHistoryStartTs = value;
  },
});

function suggestedName(exchange: string): string {
  const location = getLocationData(exchange);
  const nonce = get(connectedExchanges).filter(({ location }) => location === exchange).length + 1;
  return location ? `${location.name} ${nonce}` : '';
}

function toggleEdit() {
  set(editKeys, !get(editKeys));

  // Backing out of a key replacement drops whatever was typed, so the stored pair stands.
  if (!get(editKeys)) {
    form.state.apiKey = '';
    form.state.apiSecret = '';
  }
}

/**
 * Spelled out per option rather than built by interpolation, so that adding one fails typecheck here
 * instead of silently falling back to the raw identifier, and so the keys stay visible to the i18n
 * lint rules. The same holds for the two records below it.
 */
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

// The dialog keeps its prompt-on-close flag across opens, so hand it back disarmed.
onUnmounted(() => {
  set(stateUpdated, false);
});

/**
 * The dialog owns the entry, so a write to `modelValue` only comes back on the next tick. Every
 * caller therefore hands the entry it just wrote straight to the baseline instead of reading it
 * back: re-reading `modelValue` here returns the value from before the write, which re-takes the
 * baseline the form already had and leaves the write itself looking like a user edit.
 */
function replaceEntry(next: ExchangeFormData): void {
  set(modelValue, next);
  form.reset(toExchangeKeysFormState(next));
}

function onExchangeChange(exchange?: string) {
  const name = exchange ?? '';
  const isKraken = name === 'kraken';

  replaceEntry({
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
}

/**
 * Fills the name field with the suggestion for the chosen exchange, once, on mount.
 *
 * @remarks
 * Goes through `replaceEntry` because seeding lands after `useForm` took its baseline. Writing the
 * state directly would leave a dialog the user has not touched counting as dirty, prompting to
 * discard on close.
 *
 * The locations come from the backend, so the store holds none until that fetch lands and the
 * suggestion comes back empty. Since this runs once, writing an empty suggestion over the name would
 * leave the field blank with nothing left to restore it.
 */
function seedName(): void {
  const model = get(modelValue);

  if (get(editMode)) {
    replaceEntry({ ...model, newName: model.name });
    return;
  }

  const suggestion = suggestedName(model.location);
  if (!suggestion)
    return;

  replaceEntry({ ...model, name: suggestion });
}

onMounted(seedName);

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div
    data-testid="exchange-keys"
    class="flex flex-col gap-4"
  >
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <ExchangeInput
        show-with-key-only
        :model-value="modelValue.location"
        :label="t('common.exchange')"
        data-testid="exchange"
        :disabled="editMode"
        @update:model-value="onExchangeChange($event)"
      />

      <RuiTextField
        v-model="name"
        variant="outlined"
        color="primary"
        :error-messages="editMode ? form.errors('newName') : form.errors('name')"
        data-testid="name"
        :label="t('common.name')"
      />
    </div>

    <RuiMenuSelect
      v-if="isKraken"
      v-model="form.state.krakenAccountType"
      data-testid="account-type"
      :options="krakenAccountTypes"
      :label="t('exchange_settings.inputs.kraken_account')"
      key-attr="identifier"
      text-attr="label"
      variant="outlined"
    />

    <RuiMenuSelect
      v-if="isGate"
      v-model="form.state.gateLocation"
      data-testid="gate-location"
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
      v-model="form.state.okxLocation"
      data-testid="okx-location"
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
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            data-testid="toggle-edit-keys"
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
          data-testid="api-key"
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
          data-testid="api-secret"
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
          v-model.trim="form.state.passphrase"
          :disabled="editMode && !editKeys"
          variant="outlined"
          color="primary"
          :error-messages="form.errors('passphrase')"
          prepend-icon="lu-key"
          data-testid="passphrase"
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
      v-model:api-key="form.state.krakenFuturesApiKey"
      v-model:api-secret="form.state.krakenFuturesApiSecret"
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
      @update:selection="form.state.binanceMarkets = $event"
    />
  </div>

  <ExchangeNotices :location="modelValue.location" />
</template>
