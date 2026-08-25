<script setup lang="ts">
import { type LocationProgress, LocationStatus } from '../types';
import LocationProgressItem from './LocationProgressItem.vue';

const { locations } = defineProps<{
  locations: LocationProgress[];
}>();

const { t } = useI18n({ useScope: 'global' });

const showCompleted = ref<boolean>(false);

const inProgressLocations = computed<LocationProgress[]>(() =>
  locations.filter(l => l.status !== LocationStatus.COMPLETE && l.status !== LocationStatus.CANCELLED),
);

const completedLocations = computed<LocationProgress[]>(() =>
  locations.filter(l => l.status === LocationStatus.COMPLETE || l.status === LocationStatus.CANCELLED),
);

const hasInProgress = computed<boolean>(() => get(inProgressLocations).length > 0);
const completedCount = computed<number>(() => get(completedLocations).length);
const hasCompleted = computed<boolean>(() => !!get(completedCount));
const hasCancelledLocations = computed<boolean>(() => get(completedLocations).some(l => l.status === LocationStatus.CANCELLED));

const completedIconColor = computed<string>(() =>
  get(hasCancelledLocations) ? 'text-rui-warning' : 'text-rui-success',
);

// A cancelled location sits in this group too, so the summary must not claim completion for it —
// the rows inside already say cancelled.
const completedLabel = computed<string>(() => {
  const count = get(completedCount);
  return get(hasCancelledLocations)
    ? t('sync_progress.finished_locations', { count }, count)
    : t('sync_progress.completed_locations', { count }, count);
});

const completedIcon = computed<string>(() => (get(hasCancelledLocations) ? 'lu-circle-alert' : 'lu-circle-check'));

function toggleCompleted(): void {
  set(showCompleted, !get(showCompleted));
}
</script>

<template>
  <div class="space-y-1 rounded-lg border border-default bg-rui-grey-50 dark:bg-rui-grey-800 p-2">
    <!-- In-progress locations shown first -->
    <LocationProgressItem
      v-for="location in inProgressLocations"
      :key="`${location.location}-${location.name}`"
      :location="location"
    />

    <!-- Completed locations collapsible section -->
    <div v-if="hasCompleted">
      <button
        v-if="!showCompleted"
        type="button"
        class="w-full flex items-center gap-2 py-2 px-2 text-sm text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700 rounded-md transition-colors"
        :class="{ 'mt-2 border-t border-default pt-3': hasInProgress }"
        @click="toggleCompleted()"
      >
        <RuiIcon
          :name="completedIcon"
          :class="completedIconColor"
          size="16"
        />
        <span>{{ completedLabel }}</span>
        <RuiIcon
          name="lu-chevron-down"
          size="16"
          class="ml-auto"
        />
      </button>

      <template v-else>
        <button
          type="button"
          class="w-full flex items-center gap-2 py-2 px-2 text-sm text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700 rounded-md transition-colors"
          :class="{ 'mt-2 border-t border-default pt-3': hasInProgress }"
          @click="toggleCompleted()"
        >
          <RuiIcon
            :name="completedIcon"
            :class="completedIconColor"
            size="16"
          />
          <span>{{ completedLabel }}</span>
          <RuiIcon
            name="lu-chevron-up"
            size="16"
            class="ml-auto"
          />
        </button>

        <div class="mt-1">
          <LocationProgressItem
            v-for="location in completedLocations"
            :key="`${location.location}-${location.name}`"
            :location="location"
            compact
          />
        </div>
      </template>
    </div>
  </div>
</template>
