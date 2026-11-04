<script setup lang="ts">
import type { DeepReadonly } from 'vue';
import type { ImportLocationResolution } from './import-location-types';
import type { LocationFormData } from '@/modules/locations/location-form';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import LocationFormDialog from '@/modules/locations/components/LocationFormDialog.vue';

const model = defineModel<Record<string, string>>({ required: true });
/** Whether the chosen locations are kept as aliases, so the next import resolves them itself. */
const saveAsAliases = defineModel<boolean>('saveAsAliases', { required: true });

const { locations } = defineProps<{
  /** The values that need a location: unknown or ambiguous, never resolved ones. */
  locations: readonly DeepReadonly<ImportLocationResolution>[];
}>();

interface MappingRow {
  readonly entry: DeepReadonly<ImportLocationResolution>;
  readonly chosen: boolean;
  /** The options offered; empty offers every assignable location. */
  readonly options: readonly string[];
  readonly status: string;
}

const EVERY_LOCATION: readonly string[] = [];

const newLocation = ref<LocationFormData>();
/** The value a location is being created for, which the created location is then chosen for. */
const creatingFor = shallowRef<string>();
/** The locations created from this panel. */
const created = shallowRef<ReadonlySet<string>>(new Set());

const { t } = useI18n({ useScope: 'global' });

/** Each value with what its row shows. */
const rows = computed<MappingRow[]>(() => locations.map((entry) => {
  const choice = get(model)[entry.value] ?? '';
  return { chosen: !!choice, entry, options: optionsFor(entry, choice), status: statusOf(entry, choice) };
}));

const chosenCount = computed<number>(() => get(rows).filter(row => row.chosen).length);

/**
 * The locations a value can be mapped to.
 *
 * @remarks
 * An ambiguous value is offered its candidates, plus its current choice when that is not one of
 * them, which is a location created for it: the selector would otherwise clear a choice it does
 * not offer. An unknown value is offered every location, through one shared empty list so that
 * picking in another row does not rebuild its options.
 */
function optionsFor(entry: DeepReadonly<ImportLocationResolution>, choice: string): readonly string[] {
  if (entry.status !== 'ambiguous')
    return EVERY_LOCATION;
  if (choice && !entry.candidates.includes(choice))
    return [...entry.candidates, choice];
  return entry.candidates;
}

function statusOf(entry: DeepReadonly<ImportLocationResolution>, choice: string): string {
  if (choice && get(created).has(choice))
    return t('import_data.location_mapping.created');
  return entry.status === 'ambiguous'
    ? t('import_data.location_mapping.ambiguous', { count: entry.candidates.length })
    : t('import_data.location_mapping.unknown');
}

function updateMapping(value: string, destination: string): void {
  set(model, { ...get(model), [value]: destination });
}

function create(value: string): void {
  set(creatingFor, value);
  set(newLocation, { mode: 'add', name: value.trim(), parentIdentifier: '' });
}

/** Chooses a location created here for the value it was created for. */
function onSaved(identifier: string): void {
  const value = get(creatingFor);
  if (value === undefined)
    return;
  set(created, new Set([...get(created), identifier]));
  updateMapping(value, identifier);
  set(creatingFor, undefined);
}
</script>

<template>
  <section
    class="flex flex-col rounded-md border border-rui-divider"
    data-testid="import-location-mappings"
  >
    <header class="flex items-start gap-3 border-b border-rui-divider px-4 py-3">
      <div class="flex grow flex-col gap-0.5">
        <h3 class="text-subtitle-1 font-medium">
          {{ t('import_data.location_mapping.title') }}
        </h3>
        <p class="text-body-2 text-rui-text-secondary">
          {{ t('import_data.location_mapping.description') }}
        </p>
      </div>
      <span
        class="shrink-0 whitespace-nowrap pt-0.5 text-body-2 text-rui-text-secondary"
        data-testid="import-location-progress"
      >
        {{ t('import_data.location_mapping.progress', { chosen: chosenCount, total: rows.length }) }}
      </span>
    </header>
    <ul class="m-0 list-none divide-y divide-rui-divider p-0">
      <li
        v-for="{ chosen, entry, options, status } in rows"
        :key="entry.value"
        class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 px-4 py-3 md:grid-cols-[14rem_minmax(0,1fr)_auto] md:gap-x-4"
        data-testid="import-location-mapping"
        :data-key="entry.value"
      >
        <div class="col-span-2 flex min-w-0 items-start gap-2 md:col-span-1">
          <RuiIcon
            :name="chosen ? 'lu-circle-check' : 'lu-circle-dashed'"
            :class="chosen ? 'text-rui-success' : 'text-rui-text-disabled'"
            class="mt-0.5 shrink-0"
            size="18"
          />
          <div class="flex min-w-0 flex-col">
            <span
              v-if="entry.value.trim()"
              class="truncate font-medium"
              :title="entry.value"
            >
              {{ entry.value }}
            </span>
            <span
              v-else
              class="font-medium italic text-rui-text-secondary"
            >
              {{ t('import_data.location_mapping.empty_value') }}
            </span>
            <span
              class="truncate text-caption text-rui-text-secondary"
              data-testid="import-location-status"
            >
              {{ status }}
            </span>
          </div>
        </div>
        <LocationSelector
          :model-value="model[entry.value] ?? ''"
          class="min-w-0"
          :items="options"
          :label="t('import_data.location_mapping.choose')"
          :placeholder="t('import_data.location_mapping.choose')"
          label-placement="hidden"
          dense
          hide-details
          variant="outlined"
          data-testid="import-location-choice"
          @update:model-value="updateMapping(entry.value, $event)"
        />
        <RuiTooltip
          :open-delay="400"
          :popper="{ placement: 'top' }"
        >
          <template #activator>
            <RuiButton
              variant="text"
              color="primary"
              class="shrink-0"
              data-testid="import-location-create"
              @click="create(entry.value)"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-plus"
                  size="16"
                />
              </template>
              {{ t('import_data.location_mapping.create') }}
            </RuiButton>
          </template>
          {{ t('import_data.location_mapping.create_hint') }}
        </RuiTooltip>
      </li>
    </ul>
    <footer class="border-t border-rui-divider px-4 py-2">
      <RuiCheckbox
        v-model="saveAsAliases"
        color="primary"
        hide-details
        size="sm"
        data-testid="import-location-save-aliases"
      >
        {{ t('import_data.location_mapping.save_aliases') }}
      </RuiCheckbox>
    </footer>
    <LocationFormDialog
      v-model="newLocation"
      @saved="onSaved($event)"
    />
  </section>
</template>
