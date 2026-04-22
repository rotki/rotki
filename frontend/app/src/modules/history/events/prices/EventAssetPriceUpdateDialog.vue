<script setup lang="ts">
import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import { bigNumberify, toSentenceCase } from '@rotki/common';
import { startPromise } from '@shared/utils';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { type EventPriceUpdateMode, useEventPriceUpdate } from '@/modules/history/events/prices/use-event-price-update';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const modelValue = defineModel<EventPriceUpdatePayload | undefined>({ required: true });

const { t } = useI18n({ useScope: 'global' });
const { notifyError, notifyInfo } = useNotifications();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { fetchExistingEntry, updatePrice } = useEventPriceUpdate();

const price = ref<string>('');
const mode = ref<EventPriceUpdateMode>('manual');
const existingEntry = ref<OraclePriceEntry>();
const loading = ref<boolean>(false);
const saving = ref<boolean>(false);

const open = computed<boolean>(() => modelValue.value !== undefined);

function close(): void {
  set(modelValue, undefined);
}

const existingIsManual = computed<boolean>(() => get(existingEntry)?.sourceType === PriceOracle.MANUAL);
const showModeChoice = computed<boolean>(() => Boolean(get(existingEntry)) && !get(existingIsManual));

const priceValid = computed<boolean>(() => {
  const value = get(price).trim();
  if (!value)
    return false;
  const parsed = bigNumberify(value);
  return parsed.isFinite() && parsed.isGreaterThan(0);
});

const priceErrors = computed<string[]>(() => {
  const value = get(price).trim();
  if (!value || get(priceValid))
    return [];
  return [t('event_asset_price_update.price_error')];
});

async function load(payload: EventPriceUpdatePayload): Promise<void> {
  set(loading, true);
  set(existingEntry, undefined);
  set(price, '');
  try {
    const quote = get(currencySymbol);
    const entry = await fetchExistingEntry(payload.asset, quote, payload.timestamp);
    set(existingEntry, entry);
    if (entry) {
      set(price, entry.price.toFixed());
      set(mode, entry.sourceType === PriceOracle.MANUAL ? 'manual' : 'oracle');
    }
    else {
      set(mode, 'manual');
    }
  }
  catch (error: unknown) {
    logger.error('Failed to load existing oracle price entry:', error);
    notifyError(
      t('event_asset_price_update.fetch_error.title'),
      t('event_asset_price_update.fetch_error.description', { error: getErrorMessage(error) }),
    );
  }
  finally {
    set(loading, false);
  }
}

async function save(): Promise<void> {
  const payload = get(modelValue);
  if (!payload)
    return;

  const entry = get(existingEntry);
  const nextPrice = get(price).trim();
  const selectedMode = get(mode);
  const unchanged = entry
    && bigNumberify(nextPrice).isEqualTo(entry.price)
    && (selectedMode === 'oracle' || entry.sourceType === PriceOracle.MANUAL);
  if (unchanged) {
    close();
    return;
  }

  set(saving, true);
  try {
    await updatePrice({
      existingEntry: entry,
      fromAsset: payload.asset,
      mode: selectedMode,
      price: nextPrice,
      timestampMs: payload.timestamp,
      toAsset: get(currencySymbol),
    });
    notifyInfo(
      t('event_asset_price_update.success.title'),
      t('event_asset_price_update.success.description'),
    );
    set(modelValue, undefined);
  }
  catch (error: unknown) {
    logger.error('Failed to update event price:', error);
    notifyError(
      t('event_asset_price_update.save_error.title'),
      t('event_asset_price_update.save_error.description', { error: getErrorMessage(error) }),
    );
  }
  finally {
    set(saving, false);
  }
}

watch(modelValue, (payload) => {
  if (payload)
    startPromise(load(payload));
}, { immediate: true });
</script>

<template>
  <RuiDialog
    :model-value="open"
    max-width="500"
    @update:model-value="close()"
  >
    <RuiCard content-class="!pb-0">
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 pt-2">
          <CardTitle>
            {{ t('event_asset_price_update.title') }}
          </CardTitle>
          <RuiButton
            variant="text"
            icon
            @click="close()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </template>

      <div
        v-if="modelValue"
        class="flex flex-col gap-4"
      >
        <div class="text-sm text-rui-text-secondary">
          {{ t('event_asset_price_update.description') }}
        </div>

        <div class="flex items-center justify-between gap-3 rounded-md bg-rui-grey-50 dark:bg-rui-grey-900 px-3 py-2">
          <AssetDetails
            :asset="modelValue.asset"
            size="28px"
            hide-menu
          />
          <div class="flex flex-col items-end">
            <div class="!text-[10px] !leading-[1] text-caption text-rui-text-secondary uppercase">
              {{ t('common.datetime') }}
            </div>
            <DateDisplay
              :timestamp="modelValue.timestamp"
              milliseconds
              class="text-xs"
            />
          </div>
        </div>

        <div
          v-if="loading || showModeChoice"
          class="min-h-[2.25rem] flex items-center justify-center"
        >
          <RuiProgress
            v-if="loading"
            circular
            size="28"
            variant="indeterminate"
            color="primary"
          />
          <RuiButtonGroup
            v-else-if="showModeChoice"
            v-model="mode"
            color="primary"
            required
            variant="outlined"
            size="sm"
            class="w-full"
          >
            <RuiButton
              model-value="oracle"
              class="flex-1"
              @click="mode = 'oracle'"
            >
              {{ t('event_asset_price_update.mode.oracle.label', { source: toSentenceCase(existingEntry?.sourceType ?? '') }) }}
            </RuiButton>
            <RuiButton
              model-value="manual"
              class="flex-1"
              @click="mode = 'manual'"
            >
              {{ t('event_asset_price_update.mode.manual.label') }}
            </RuiButton>
          </RuiButtonGroup>
        </div>

        <AmountInput
          v-model="price"
          variant="outlined"
          :label="t('event_asset_price_update.price_label', { symbol: currencySymbol })"
          :disabled="loading || saving"
          :error-messages="priceErrors"
        />
      </div>

      <template #footer>
        <div class="flex justify-end gap-2 w-full">
          <RuiButton
            variant="text"
            :disabled="saving"
            @click="close()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :loading="saving"
            :disabled="loading || !priceValid"
            @click="save()"
          >
            {{ t('common.actions.save') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
