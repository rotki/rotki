<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import type { LocationDataSnapshotPayload } from '@/types/snapshots';

const props = withDefaults(
  defineProps<{
    form: LocationDataSnapshotPayload;
    excludedLocations?: string[];
  }>(),
  {
    excludedLocations: () => [],
  },
);

const emit = defineEmits<{
  (e: 'update:form', payload: LocationDataSnapshotPayload): void;
}>();

const location = usePropVModel(props, 'form', 'location', emit);
const value = usePropVModel(props, 'form', 'usdValue', emit);

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

const { setValidation } = useEditLocationsSnapshotForm();

const v$ = setValidation(
  rules,
  {
    location,
    value,
  },
  { $autoDirty: true },
);
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
