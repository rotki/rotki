<script setup lang="ts">
import type { ImportLocationResolution } from './import-location-types';
import LocationSelector from '@/modules/balances/LocationSelector.vue';

const model = defineModel<Record<string, string>>({ required: true });

const { locations } = defineProps<{
  locations: ImportLocationResolution[];
}>();

const { t } = useI18n({ useScope: 'global' });

const pendingLocations = computed<ImportLocationResolution[]>(() => locations.filter(entry => entry.status !== 'resolved'));

function updateMapping(value: string, destination: string): void {
  set(model, { ...get(model), [value]: destination });
}
</script>

<template>
  <section
    v-if="pendingLocations.length > 0"
    class="flex flex-col gap-4"
  >
    <div>
      <h3 class="text-h6">
        {{ t('import_data.location_mapping.title') }}
      </h3>
      <p class="text-body-2 text-rui-text-secondary">
        {{ t('import_data.location_mapping.description') }}
      </p>
    </div>
    <div
      v-for="entry in pendingLocations"
      :key="entry.value"
      data-testid="import-location-mapping"
      :data-key="entry.value"
    >
      <LocationSelector
        :model-value="model[entry.value] ?? ''"
        :label="entry.value || t('import_data.location_mapping.empty_value')"
        variant="outlined"
        @update:model-value="updateMapping(entry.value, $event)"
      />
    </div>
  </section>
</template>
