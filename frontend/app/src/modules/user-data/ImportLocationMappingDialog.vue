<script setup lang="ts">
import type { DeepReadonly } from 'vue';
import type { LocationFormData } from '@/modules/locations/location-form';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import type { ImportLocationResolution } from '@/modules/user-data/use-import-data-api';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import LocationFormDialog from '@/modules/locations/components/LocationFormDialog.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const { resolutions } = defineProps<{
  /** The location values of the file that resolve to no location or to several. */
  resolutions: DeepReadonly<ImportLocationResolution[]> | undefined;
}>();

const emit = defineEmits<{
  confirm: [choice: { mappings: Record<string, string>; saveAsAliases: boolean }];
  cancel: [];
}>();

const mappings = ref<Record<string, string>>({});
const saveAsAliases = ref<boolean>(true);
const newLocation = ref<LocationFormData>();
/** The value a location is being created for, which the created location is then chosen for. */
const creatingFor = shallowRef<string>();

const { t } = useI18n({ useScope: 'global' });

const complete = computed<boolean>(() => (resolutions ?? []).every(resolution => !!get(mappings)[resolution.value]));

watch(() => resolutions, () => {
  set(mappings, {});
  set(saveAsAliases, true);
});

function create(value: string): void {
  set(creatingFor, value);
  set(newLocation, { mode: 'add', name: value, parentIdentifier: '' });
}

function onCreated(location: LocationNode): void {
  const value = get(creatingFor);
  if (value !== undefined)
    set(mappings, { ...get(mappings), [value]: location.identifier });
  set(creatingFor, undefined);
}

function confirm(): void {
  if (get(complete))
    emit('confirm', { mappings: { ...get(mappings) }, saveAsAliases: get(saveAsAliases) });
}
</script>

<template>
  <BigDialog
    :display="!!resolutions"
    :title="t('import_data.location_mapping.title')"
    :subtitle="t('import_data.location_mapping.subtitle')"
    :action="{ disabled: !complete, primary: t('common.actions.import') }"
    @confirm="confirm()"
    @cancel="emit('cancel')"
  >
    <div
      class="flex flex-col gap-4"
      data-testid="import-location-mapping"
    >
      <div
        v-for="resolution in resolutions"
        :key="resolution.value"
        class="flex flex-col gap-2"
        data-testid="import-location-value"
        :data-value="resolution.value"
      >
        <div class="flex items-center gap-2">
          <span class="font-medium">{{ resolution.value }}</span>
          <RuiChip
            size="sm"
            :color="resolution.status === 'ambiguous' ? 'warning' : 'error'"
          >
            {{ resolution.status === 'ambiguous' ? t('import_data.location_mapping.ambiguous') : t('import_data.location_mapping.unknown') }}
          </RuiChip>
        </div>
        <div class="flex items-start gap-2">
          <LocationSelector
            :model-value="mappings[resolution.value] ?? ''"
            class="grow"
            dense
            :items="resolution.status === 'ambiguous' ? resolution.candidates : []"
            :label="t('common.location')"
            hide-details
            data-testid="import-location-choice"
            @update:model-value="mappings = { ...mappings, [resolution.value]: $event }"
          />
          <RuiButton
            variant="outlined"
            color="primary"
            data-testid="import-location-create"
            @click="create(resolution.value)"
          >
            {{ t('import_data.location_mapping.create') }}
          </RuiButton>
        </div>
      </div>
      <RuiCheckbox
        v-model="saveAsAliases"
        color="primary"
        hide-details
        data-testid="import-location-save-aliases"
      >
        {{ t('import_data.location_mapping.save_aliases') }}
      </RuiCheckbox>
    </div>
    <LocationFormDialog
      v-model="newLocation"
      @created="onCreated($event)"
    />
  </BigDialog>
</template>
