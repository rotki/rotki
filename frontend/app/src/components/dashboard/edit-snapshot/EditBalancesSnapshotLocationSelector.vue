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
  <v-sheet outlined class="pa-4" rounded>
    <div class="text-subtitle-2 mb-3">
      {{ t('dashboard.snapshot.edit.dialog.balances.optional') }}
    </div>
    <div>
      <location-selector
        :value="value"
        :items="locations"
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
      <div class="d-flex align-center mt-2">
        <div>
          <div class="text-overline text--secondary mb-n2">
            {{ t('dashboard.snapshot.edit.dialog.balances.preview.from') }}
          </div>
          <amount-display
            :value="previewLocationBalance.before"
            fiat-currency="USD"
          />
        </div>
        <div class="px-8">
          <v-icon>mdi-arrow-right</v-icon>
        </div>
        <div>
          <div class="text-overline text--secondary mb-n2">
            {{ t('dashboard.snapshot.edit.dialog.balances.preview.to') }}
          </div>
          <amount-display
            :value="previewLocationBalance.after"
            fiat-currency="USD"
          />
        </div>
      </div>
    </div>
  </v-sheet>
</template>
