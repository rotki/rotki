<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { type LocationDataSnapshotPayload } from '@/types/snapshots';
import { toMessages } from '@/utils/validation';

const props = withDefaults(
  defineProps<{
    form: LocationDataSnapshotPayload;
    excludedLocations?: string[];
  }>(),
  {
    excludedLocations: () => []
  }
);

const emit = defineEmits<{
  (e: 'update:form', payload: LocationDataSnapshotPayload): void;
}>();

const { form } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();

const updateForm = (partial: Partial<LocationDataSnapshotPayload>) => {
  emit('update:form', {
    ...(get(form) as LocationDataSnapshotPayload),
    ...partial
  });
};

const rules = {
  location: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.location_data.rules.location'),
      required
    )
  },
  value: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.location_data.rules.value'),
      required
    )
  }
};

const { setValidation } = useEditLocationsSnapshotForm();

const v$ = setValidation(
  rules,
  {
    location: computed(() => get(form).location),
    value: computed(() => get(form).usdValue)
  },
  { $autoDirty: true }
);
</script>

<template>
  <div class="pt-1 flex flex-col gap-4">
    <LocationSelector
      :value="form.location"
      :excludes="excludedLocations"
      outlined
      :label="t('common.location')"
      :error-messages="toMessages(v$.location)"
      @input="updateForm({ location: $event })"
    />
    <AmountInput
      :value="form.usdValue"
      outlined
      :label="
        t('common.value_in_symbol', {
          symbol: currencySymbol
        })
      "
      :error-messages="toMessages(v$.value)"
      @input="updateForm({ usdValue: $event })"
    />
  </div>
</template>
