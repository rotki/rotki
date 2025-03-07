<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';

const model = defineModel<string>({ default: '', required: true });

withDefaults(
  defineProps<{
    locations?: string[];
    previewLocationBalance?: Record<string, BigNumber> | null;
    optionalShowExisting?: boolean;
  }>(),
  {
    locations: () => [],
    optionalShowExisting: false,
    previewLocationBalance: null,
  },
);

const { t } = useI18n();

const showOnlyExisting = ref<boolean>(true);
</script>

<template>
  <RuiCard
    variant="outlined"
    class="[&>div]:!overflow-visible"
    rounded="sm"
  >
    <div class="text-subtitle-2 mb-3">
      {{ t('common.optional') }}
    </div>
    <RuiSwitch
      v-if="optionalShowExisting"
      v-model="showOnlyExisting"
      color="primary"
      size="sm"
      hide-details
      class="[&_span]:text-sm [&_span]:mt-0.5 mb-4"
    >
      {{ t('dashboard.snapshot.edit.dialog.balances.only_show_existing') }}
    </RuiSwitch>
    <LocationSelector
      v-model="model"
      :items="showOnlyExisting ? locations : []"
      class="edit-balances-snapshot__location"
      clearable
      :menu-options="{ menuClass: 'z-[10001]' }"
      :persistent-hint="!modelValue"
      :hide-details="!!modelValue"
      :hint="t('dashboard.snapshot.edit.dialog.balances.hints.location')"
      :label="t('common.location')"
    />
    <div
      v-if="previewLocationBalance"
      class="mt-4"
    >
      <div class="text-subtitle-2">
        {{ t('dashboard.snapshot.edit.dialog.balances.preview.title') }}
      </div>
      <div class="flex items-center mt-2">
        <div>
          <div class="text-overline text-rui-text-secondary -mb-2">
            {{ t('dashboard.snapshot.edit.dialog.balances.preview.from') }}
          </div>
          <AmountDisplay
            :value="previewLocationBalance.before"
            fiat-currency="USD"
          />
        </div>
        <div class="px-8 text-rui-text-secondary">
          <RuiIcon name="lu-arrow-right" />
        </div>
        <div>
          <div class="text-overline text-rui-text-secondary -mb-2">
            {{ t('dashboard.snapshot.edit.dialog.balances.preview.to') }}
          </div>
          <AmountDisplay
            :value="previewLocationBalance.after"
            fiat-currency="USD"
          />
        </div>
      </div>
    </div>
  </RuiCard>
</template>
