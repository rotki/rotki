<script setup lang="ts">
import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import { toSentenceCase } from '@rotki/common';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useEventPriceUpdateDialog } from '@/modules/history/events/prices/use-event-price-update-dialog';
import { useSetting } from '@/modules/settings/use-setting';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const modelValue = defineModel<EventPriceUpdatePayload | undefined>({ required: true });

const { t } = useI18n({ useScope: 'global' });
const currencySymbol = useSetting('currencySymbol');

const {
  close,
  existingEntry,
  loading,
  modelMode: mode,
  modelPrice: price,
  open,
  priceErrors,
  priceValid,
  save,
  saving,
  showModeChoice,
} = useEventPriceUpdateDialog(modelValue);
</script>

<template>
  <RuiDialog
    :model-value="open"
    max-width="500"
    @update:model-value="close()"
  >
    <RuiCard :class-names="{ content: '!pb-0' }">
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
            :display="{ size: '28px' }"
            :actions="{ hideMenu: true }"
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
