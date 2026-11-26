<script setup lang="ts">
import { RuiMenuSelect } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { type MessageKey, msg } from '@/message-key';
import { GateLocation, KrakenAccountType, OkxLocation } from '@/modules/balances/types/exchanges';
import { isGate as gate, isKraken as kraken, isOkx as okx } from '@/modules/settings/api-keys/exchange/exchange-keys-form';
import GateRegionSelectorItem from '@/modules/settings/api-keys/exchange/GateRegionSelectorItem.vue';
import OkxRegionSelectorItem from '@/modules/settings/api-keys/exchange/OkxRegionSelectorItem.vue';

const krakenAccountType = defineModel<KrakenAccountType | undefined>('krakenAccountType');

const gateLocation = defineModel<GateLocation | undefined>('gateLocation');

const okxLocation = defineModel<OkxLocation | undefined>('okxLocation');

const { location } = defineProps<{
  /** The exchange being connected, which decides the one selector shown, if any. */
  location: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const isGate = computed<boolean>(() => gate(location));
const isKraken = computed<boolean>(() => kraken(location));
const isOkx = computed<boolean>(() => okx(location));

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
</script>

<template>
  <RuiMenuSelect
    v-if="isKraken"
    v-model="krakenAccountType"
    data-testid="account-type"
    :options="krakenAccountTypes"
    :label="t('exchange_settings.inputs.kraken_account')"
    key-attr="identifier"
    text-attr="label"
  />

  <RuiMenuSelect
    v-if="isGate"
    v-model="gateLocation"
    data-testid="gate-location"
    :options="gateLocations"
    :label="t('exchange_keys_form.region')"
    key-attr="identifier"
    text-attr="label"
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
    data-testid="okx-location"
    :options="okxLocations"
    :label="t('exchange_keys_form.region')"
    key-attr="identifier"
    text-attr="label"
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
</template>
