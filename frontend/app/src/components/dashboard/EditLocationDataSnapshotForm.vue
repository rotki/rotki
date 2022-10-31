<template>
  <v-form :value="value" class="pt-4" @input="input">
    <div class="mb-4">
      <location-selector
        :value="form.location"
        :excludes="excludedLocations"
        outlined
        :label="tc('common.location')"
        :rules="locationRules"
        @input="updateForm({ location: getLocation($event) })"
      />
    </div>
    <div class="mb-4">
      <amount-input
        :value="form.usdValue"
        outlined
        :label="
          tc('common.value_in_symbol', 0, {
            symbol: currencySymbol
          })
        "
        :rules="valueRules"
        @input="updateForm({ usdValue: $event })"
      />
    </div>
  </v-form>
</template>
<script setup lang="ts">
import { PropType } from 'vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { LocationDataSnapshotPayload } from '@/types/snapshots';

const props = defineProps({
  value: {
    required: false,
    type: Boolean,
    default: false
  },
  form: {
    required: true,
    type: Object as PropType<LocationDataSnapshotPayload>
  },
  excludedLocations: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  }
});

const emit = defineEmits<{
  (e: 'input', valid: boolean): void;
  (e: 'update:form', payload: LocationDataSnapshotPayload): void;
}>();

const { form } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { tc } = useI18n();

const input = (valid: boolean) => {
  emit('input', valid);
};

const updateForm = (partial: Partial<LocationDataSnapshotPayload>) => {
  emit('update:form', {
    ...(get(form) as LocationDataSnapshotPayload),
    ...partial
  });
};

const getLocation = (location: any) => location as string;

const locationRules = computed(() => [
  (v: string) =>
    !!v || tc('dashboard.snapshot.edit.dialog.location_data.rules.location')
]);

const valueRules = computed(() => [
  (v: string) =>
    !!v || tc('dashboard.snapshot.edit.dialog.location_data.rules.value')
]);
</script>
