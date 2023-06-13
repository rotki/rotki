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

const { valid, setValidation } = useEditLocationsSnapshotForm();

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
  <v-form :value="valid" class="pt-4">
    <div class="mb-4">
      <location-selector
        :value="form.location"
        :excludes="excludedLocations"
        outlined
        :label="t('common.location')"
        :error-messages="toMessages(v$.location)"
        @input="updateForm({ location: $event })"
      />
    </div>
    <div class="mb-4">
      <amount-input
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
  </v-form>
</template>
