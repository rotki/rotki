<script setup lang="ts">
import type { LocationDataSnapshotPayload } from '@/types/snapshots';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const model = defineModel<LocationDataSnapshotPayload>({ required: true });

withDefaults(
  defineProps<{
    excludedLocations?: string[];
  }>(),
  {
    excludedLocations: () => [],
  },
);

const location = useRefPropVModel(model, 'location');
const value = useRefPropVModel(model, 'usdValue');

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();

const rules = {
  location: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.location_data.rules.location'), required),
  },
  value: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.location_data.rules.value'), required),
  },
};

const states = {
  location,
  value,
};

const v$ = useVuelidate(
  rules,
  states,
  { $autoDirty: true },
);
useFormStateWatcher(states, stateUpdated);

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <form class="flex flex-col gap-2">
    <LocationSelector
      v-model="location"
      :excludes="excludedLocations"
      :label="t('common.location')"
      :error-messages="toMessages(v$.location)"
    />
    <AmountInput
      v-model="value"
      variant="outlined"
      :label="
        t('common.value_in_symbol', {
          symbol: currencySymbol,
        })
      "
      :error-messages="toMessages(v$.value)"
    />
  </form>
</template>
