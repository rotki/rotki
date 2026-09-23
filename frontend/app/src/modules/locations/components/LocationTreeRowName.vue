<script setup lang="ts">
import { type LocationRow, type NamePart, nameParts } from '@/modules/locations/location-rows';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const { row, search } = defineProps<{
  row: LocationRow;
  search: string;
}>();

const emit = defineEmits<{
  toggle: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const parts = computed<NamePart[]>(() => nameParts(row.node.name, search));
</script>

<template>
  <div
    class="flex items-center gap-2 h-7 min-w-0"
    :style="{ paddingLeft: `${row.depth * 1.5}rem` }"
    data-testid="location-row"
    :data-location="row.node.identifier"
  >
    <RuiButton
      v-if="row.hasChildren"
      variant="text"
      icon
      size="sm"
      class="!p-0 size-6 shrink-0"
      :aria-expanded="row.expanded"
      :title="row.expanded ? t('location_manager.actions.collapse') : t('location_manager.actions.expand')"
      data-testid="location-toggle-children"
      @click="emit('toggle')"
    >
      <RuiIcon
        :name="row.expanded ? 'lu-chevron-down' : 'lu-chevron-right'"
        size="16"
      />
    </RuiButton>
    <div
      v-else
      class="size-6 shrink-0"
    />
    <LocationIcon
      class="shrink-0"
      :class="{ 'opacity-50': !row.node.isActive }"
      :item="row.node.identifier"
      icon
      size="20px"
    />
    <span
      class="truncate"
      :class="row.node.isActive ? 'text-rui-text' : 'text-rui-text-disabled'"
      :title="row.node.name"
      data-testid="location-row-name"
    >
      <template
        v-for="(part, index) in parts"
        :key="index"
      >
        <mark
          v-if="part.match"
          class="bg-rui-primary/20 text-inherit rounded-sm"
          v-text="part.text"
        />
        <template v-else>{{ part.text }}</template>
      </template>
    </span>
    <RuiChip
      v-if="!row.node.isActive"
      class="shrink-0 hidden sm:inline-flex"
      size="sm"
      color="grey"
      variant="outlined"
    >
      {{ t('location_manager.archived') }}
    </RuiChip>
    <RuiChip
      v-else-if="!row.node.isBuiltin"
      class="shrink-0 hidden sm:inline-flex"
      size="sm"
      color="primary"
      variant="outlined"
    >
      {{ t('location_manager.custom') }}
    </RuiChip>
  </div>
</template>
