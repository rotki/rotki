<script setup lang="ts">
import type { ZodType } from 'zod';
import type { LocationDataSnapshotPayload } from '@/modules/dashboard/snapshots';
import { isEqual } from 'es-toolkit';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useForm } from '@/modules/core/form/use-form';
import {
  type LocationDataSnapshotFormState,
  locationDataSnapshotSchema,
} from '@/modules/dashboard/edit-snapshot/snapshot-forms';
import { useSetting } from '@/modules/settings/use-setting';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const model = defineModel<LocationDataSnapshotPayload>({ required: true });

const { excludedLocations = [] } = defineProps<{
  excludedLocations?: string[];
}>();

const currencySymbol = useSetting('currencySymbol');

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => locationDataSnapshotSchema({
  location: t('dashboard.snapshot.edit.dialog.location_data.rules.location'),
  value: t('dashboard.snapshot.edit.dialog.location_data.rules.value'),
}));

/** The dialog owns the persist and reads the payload off the model, so submitting here is a no-op. */
const form = useForm<LocationDataSnapshotFormState, LocationDataSnapshotFormState>({
  initial: (): LocationDataSnapshotFormState => ({ ...get(model) }),
  schema,
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): LocationDataSnapshotFormState => ({ ...state }),
  // The timestamp is carried, not edited; only the two fields the form gates count as an edit.
  transientKeys: ['timestamp'],
});

// The dialog reads the payload it saves straight off the model, so every edit is written back to it.
watch(() => form.state, (state) => {
  set(model, { ...state });
}, { deep: true });

// And an edit made outside the form (a reset, a different row) is pulled back in.
watch(model, (value) => {
  if (!isEqual(value, form.state))
    Object.assign(form.state, value);
}, { deep: true });

watch(form.dirty, (dirty) => {
  set(stateUpdated, dirty);
});

// The dialog keeps its prompt-on-close flag across opens, so hand it back disarmed.
onUnmounted(() => {
  set(stateUpdated, false);
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <LocationSelector
      v-model="form.state.location"
      data-testid="edit-location-location"
      :excludes="excludedLocations"
      :label="t('common.location')"
      :error-messages="form.errors('location')"
      @update:model-value="form.touch('location')"
    />
    <AmountInput
      v-model="form.state.usdValue"
      variant="outlined"
      data-testid="edit-location-value"
      :label="
        t('common.value_in_symbol', {
          symbol: currencySymbol,
        })
      "
      :error-messages="form.errors('usdValue')"
      @blur="form.touch('usdValue')"
    />
  </div>
</template>
