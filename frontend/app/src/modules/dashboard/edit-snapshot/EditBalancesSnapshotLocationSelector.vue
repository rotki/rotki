<script setup lang="ts">
import type { TradeLocationData } from '@/modules/core/common/location';
import type { LocationBalancePreview } from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';

const model = defineModel<string>({ default: '', required: true });

const { disabledLocations = [], errorMessages = [], locations = [], optionalShowExisting = false, previewLocationBalance = null, timestamp } = defineProps<{
  locations?: string[];
  previewLocationBalance?: LocationBalancePreview | null;
  optionalShowExisting?: boolean;
  errorMessages?: string[];
  /** Location identifiers that can't absorb this operation; rendered unselectable. */
  disabledLocations?: string[];
  timestamp: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const showOnlyExisting = ref<boolean>(true);

function isLocationDisabled(item: TradeLocationData): boolean {
  return disabledLocations.includes(item.identifier);
}
</script>

<template>
  <div>
    <LocationSelector
      v-model="model"
      :items="showOnlyExisting ? locations : []"
      class="edit-balances-snapshot__location"
      clearable
      :item-disabled="isLocationDisabled"
      :menu-options="{ menuClass: 'z-[10001]' }"
      :hide-details="false"
      :error-messages="errorMessages"
      :hint="t('dashboard.snapshot.edit.dialog.balances.hints.location')"
      :label="t('common.location')"
    />
    <RuiSwitch
      v-if="optionalShowExisting"
      v-model="showOnlyExisting"
      color="primary"
      size="sm"
      hide-details
      class="[&_span]:text-sm [&_span]:mt-0.5 mt-2"
    >
      {{ t('dashboard.snapshot.edit.dialog.balances.only_show_existing') }}
    </RuiSwitch>
    <p
      v-if="disabledLocations.length > 0"
      class="text-caption text-rui-text-secondary leading-relaxed mt-2"
    >
      {{ t('dashboard.snapshot.edit.dialog.balances.hints.insufficient_location') }}
    </p>
    <div
      v-if="previewLocationBalance"
      class="mt-5 flex flex-col gap-2"
    >
      <div class="text-subtitle-2">
        {{ t('dashboard.snapshot.edit.dialog.balances.preview.title') }}
      </div>
      <div class="flex items-center gap-6">
        <div class="flex flex-col gap-0.5">
          <span class="text-caption text-rui-text-secondary uppercase tracking-wide">
            {{ t('dashboard.snapshot.edit.dialog.balances.preview.from') }}
          </span>
          <SnapshotFiatDisplay
            class="font-medium"
            :value="previewLocationBalance.before"
            :timestamp="timestamp"
          />
        </div>
        <RuiIcon
          class="text-rui-text-secondary shrink-0"
          name="lu-arrow-right"
        />
        <div class="flex flex-col gap-0.5">
          <span class="text-caption text-rui-text-secondary uppercase tracking-wide">
            {{ t('dashboard.snapshot.edit.dialog.balances.preview.to') }}
          </span>
          <SnapshotFiatDisplay
            class="font-medium"
            :value="previewLocationBalance.after"
            :timestamp="timestamp"
          />
        </div>
      </div>
    </div>
  </div>
</template>
