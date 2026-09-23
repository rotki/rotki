<script setup lang="ts">
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { locationUsageEntries, type LocationUsageEntry } from '@/modules/locations/location-usage';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

const modelValue = defineModel<{ location: LocationNode; usage: Record<string, number> } | undefined>({ required: true });

const emit = defineEmits<{
  archive: [location: LocationNode];
}>();

const { t } = useI18n({ useScope: 'global' });

const { pathLabelOf } = useLocationTreeStore();

const entries = computed<LocationUsageEntry[]>(() => {
  const value = get(modelValue);
  return value ? locationUsageEntries(value.usage, value.location.identifier) : [];
});

function close(): void {
  set(modelValue, undefined);
}

function archive(): void {
  const value = get(modelValue);
  if (value)
    emit('archive', value.location);
  close();
}
</script>

<template>
  <RuiDialog
    :model-value="!!modelValue"
    max-width="500"
    @update:model-value="!$event && close()"
  >
    <RuiCard
      v-if="modelValue"
      data-testid="location-usage-dialog"
    >
      <template #header>
        {{ t('location_manager.usage.title', { name: pathLabelOf(modelValue.location.identifier) }) }}
      </template>
      <p class="text-body-2 text-rui-text-secondary mb-4">
        {{ t('location_manager.usage.message') }}
      </p>
      <ul class="flex flex-col gap-1 list-none pl-0">
        <li
          v-for="entry in entries"
          :key="entry.kind"
          class="flex items-center justify-between gap-4"
          data-testid="location-usage-entry"
        >
          <RouterLink
            v-if="entry.to"
            :to="entry.to"
            class="text-rui-primary underline"
            data-testid="location-usage-link"
            @click="close()"
          >
            {{ entry.labelKey ? t(entry.labelKey) : entry.kind }}
          </RouterLink>
          <span v-else>{{ entry.labelKey ? t(entry.labelKey) : entry.kind }}</span>
          <span class="font-medium">{{ entry.count }}</span>
        </li>
      </ul>
      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          @click="close()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
        <RuiButton
          v-if="modelValue.location.isActive"
          color="primary"
          data-testid="location-usage-archive"
          @click="archive()"
        >
          {{ t('location_manager.actions.archive') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
