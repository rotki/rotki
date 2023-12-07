<script setup lang="ts">
import { type BigNumber } from '@rotki/common';

withDefaults(
  defineProps<{
    value?: string;
    locations?: string[];
    previewLocationBalance?: Record<string, BigNumber> | null;
  }>(),
  {
    value: '',
    locations: () => [],
    previewLocationBalance: null
  }
);

const emit = defineEmits<{
  (e: 'input', location: string): void;
}>();
const input = (location: string) => {
  emit('input', location);
};

const { t } = useI18n();
</script>

<template>
  <RuiCard
    variant="outlined"
    class="[&>div]:!overflow-visible"
    rounded="sm"
    no-padding
  >
    <div class="text-subtitle-2 mb-3">
      {{ t('dashboard.snapshot.edit.dialog.balances.optional') }}
    </div>
    <div>
      <LocationSelector
        :value="value"
        :items="locations"
        class="edit-balances-snapshot__location"
        attach=".edit-balances-snapshot__location"
        :menu-props="{ top: true }"
        outlined
        clearable
        :persistent-hint="!value"
        :hide-details="!!value"
        :hint="t('dashboard.snapshot.edit.dialog.balances.hints.location')"
        :label="t('common.location')"
        @input="input($event)"
      />
    </div>
    <div v-if="previewLocationBalance" class="mt-4">
      <div class="text-subtitle-2">
        {{ t('dashboard.snapshot.edit.dialog.balances.preview.title') }}
      </div>
      <div class="flex items-center mt-2">
        <div>
          <div class="text-overline text--secondary mb-n2">
            {{ t('dashboard.snapshot.edit.dialog.balances.preview.from') }}
          </div>
          <AmountDisplay
            :value="previewLocationBalance.before"
            fiat-currency="USD"
          />
        </div>
        <div class="px-8 text-rui-text-secondary">
          <RuiIcon name="arrow-right-line" />
        </div>
        <div>
          <div class="text-overline text--secondary mb-n2">
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
