<script setup lang="ts">
import { RuiButton, RuiButtonGroup } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, onMounted, type Ref, type WritableComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { AccountHistoryRange } from '@/modules/balances/account-history/account-history-selection';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import LocationLabelSelector from '@/modules/history/LocationLabelSelector.vue';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useHistoryStore } from '@/modules/history/use-history-store';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const account = defineModel<string | undefined>('account', { required: true });
const asset = defineModel<string | undefined>('asset', { required: true });
const location = defineModel<string | undefined>('location', { required: true });
const range = defineModel<AccountHistoryRange>('range', { required: true });

const { assets, assetsLoading = false, assetsProcessingRequired = false, locations } = defineProps<{
  /** The assets the account has ever held; the asset picker offers only these. */
  assets: string[];
  assetsLoading?: boolean;
  /** The account's events are not all processed yet, so `assets` may be missing some. */
  assetsProcessingRequired?: boolean;
  /** The locations the account holds the asset in. */
  locations: string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const { locationLabels } = storeToRefs(useHistoryStore());
const { fetchLocationLabels } = useHistoryDataFetching();

/** The pickers write `''` when nothing is picked; the selection keeps that as unset. */
function emptyAsUnset(model: Ref<string | undefined>): WritableComputedRef<string> {
  return computed<string>({
    get: () => get(model) ?? '',
    set: (value: string) => {
      set(model, value || undefined);
    },
  });
}

const accountValue = emptyAsUnset(account);

/**
 * The asset the picker shows, held back until the account's asset list is in.
 *
 * @remarks
 * The picker clears a selection that was visible and then is not. Given the asset before the list
 * arrives, it shows it as an unrestricted pick, then hides it while the list's labels resolve, and
 * clears it: a linked page lost its asset on load. Handing it over with the list avoids that.
 * While it is held back the picker writes back the empty value it was given, which is not a pick
 * and is ignored; an empty value written later is a clear.
 */
const assetValue = computed<string | undefined>({
  get: () => (assets.length > 0 ? get(asset) : undefined),
  set: (value: string | undefined) => {
    if (assets.length > 0)
      set(asset, value || undefined);
  },
});

const locationValue = emptyAsUnset(location);

const ranges = computed<{ value: AccountHistoryRange; label: string }[]>(() => [
  { label: t('account_history.range.month'), value: AccountHistoryRange.MONTH },
  { label: t('account_history.range.quarter'), value: AccountHistoryRange.QUARTER },
  { label: t('account_history.range.half_year'), value: AccountHistoryRange.HALF_YEAR },
  { label: t('account_history.range.year'), value: AccountHistoryRange.YEAR },
  { label: t('account_history.range.all'), value: AccountHistoryRange.ALL },
]);

onMounted(() => {
  if (get(locationLabels).length === 0)
    startPromise(fetchLocationLabels());
});
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
      <LocationLabelSelector
        v-model="accountValue"
        :options="locationLabels"
        :label="t('account_history.selectors.account')"
        hide-details
        data-testid="account-history-account"
      />
      <AssetSelect
        v-model="assetValue"
        clearable
        :label="t('account_history.selectors.asset')"
        :hint="assetsProcessingRequired ? t('account_history.selectors.asset_hint_processing') : t('account_history.selectors.asset_hint')"
        :source="{ items: assets, showIgnored: true }"
        :disabled="!account || assetsLoading"
        data-testid="account-history-asset"
      />
      <LocationSelector
        v-model="locationValue"
        :items="locations"
        clearable
        :label="t('account_history.selectors.location')"
        :hint="t('account_history.selectors.location_hint')"
        :disabled="locations.length < 2"
        data-testid="account-history-location"
      />
    </div>
    <RuiButtonGroup
      v-model="range"
      variant="segmented"
      required
      class="self-start"
      data-testid="account-history-range"
    >
      <RuiButton
        v-for="option in ranges"
        :key="option.value"
        :model-value="option.value"
        :data-testid="`account-history-range-${option.value}`"
      >
        {{ option.label }}
      </RuiButton>
    </RuiButtonGroup>
  </div>
</template>
