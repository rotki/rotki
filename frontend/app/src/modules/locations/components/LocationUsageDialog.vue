<script setup lang="ts">
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { locationUsageEntries, type LocationUsageEntry } from '@/modules/locations/location-usage';

const modelValue = defineModel<{ location: LocationNode; usage: Record<string, number> } | undefined>({ required: true });

const emit = defineEmits<{
  archive: [location: LocationNode];
}>();

const { t } = useI18n({ useScope: 'global' });

const entries = computed<LocationUsageEntry[]>(() => {
  const value = get(modelValue);
  return value ? locationUsageEntries(value.usage) : [];
});

function archive(): void {
  const value = get(modelValue);
  if (value)
    emit('archive', value.location);
  set(modelValue, undefined);
}
</script>

<template>
  <RuiDialog
    :model-value="!!modelValue"
    max-width="500"
    @update:model-value="!$event && (modelValue = undefined)"
  >
    <RuiCard
      v-if="modelValue"
      data-testid="location-usage-dialog"
    >
      <template #header>
        {{ t('location_manager.usage.title', { name: modelValue.location.name }) }}
      </template>
      <p class="text-body-2 text-rui-text-secondary mb-4">
        {{ t('location_manager.usage.message') }}
      </p>
      <ul class="flex flex-col gap-1">
        <li
          v-for="entry in entries"
          :key="entry.kind"
          class="flex justify-between"
          data-testid="location-usage-entry"
        >
          <span>{{ entry.labelKey ? t(entry.labelKey) : entry.kind }}</span>
          <span class="font-medium">{{ entry.count }}</span>
        </li>
      </ul>
      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          @click="modelValue = undefined"
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
