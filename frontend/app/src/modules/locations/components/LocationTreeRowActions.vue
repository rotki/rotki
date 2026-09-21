<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';

const { node } = defineProps<{
  node: LocationNode;
}>();

const emit = defineEmits<{
  'add-child': [];
  'toggle-archive': [];
  'edit': [];
  'delete': [];
}>();

interface RowAction {
  readonly key: 'add-child' | 'toggle-archive' | 'edit' | 'delete';
  readonly icon: RuiIcons;
  readonly label: string;
  readonly testId: string;
  readonly danger?: boolean;
}

const { t } = useI18n({ useScope: 'global' });
const { isSmAndDown } = useBreakpoint();

/**
 * The actions of the row, one slot each so that every icon sits in the same column on every row;
 * an action that does not apply leaves its slot empty.
 */
const slots = computed<(RowAction | undefined)[]>(() => {
  const custom = !node.isBuiltin;
  return [
    node.isActive
      ? { icon: 'lu-plus', key: 'add-child', label: t('location_manager.actions.add_child'), testId: 'location-add-child' }
      : undefined,
    custom
      ? {
          icon: node.isActive ? 'lu-archive' : 'lu-undo-2',
          key: 'toggle-archive',
          label: node.isActive ? t('location_manager.actions.archive') : t('location_manager.actions.unarchive'),
          testId: 'location-toggle-archive',
        }
      : undefined,
    custom ? { icon: 'lu-pencil', key: 'edit', label: t('common.actions.edit'), testId: 'row-edit' } : undefined,
    custom ? { danger: true, icon: 'lu-trash-2', key: 'delete', label: t('common.actions.delete'), testId: 'row-delete' } : undefined,
  ];
});

const available = computed<RowAction[]>(() => get(slots).filter((action): action is RowAction => action !== undefined));

function run(action: RowAction): void {
  switch (action.key) {
    case 'add-child':
      return emit('add-child');
    case 'toggle-archive':
      return emit('toggle-archive');
    case 'edit':
      return emit('edit');
    case 'delete':
      return emit('delete');
  }
}
</script>

<template>
  <RuiMenu
    v-if="isSmAndDown && available.length > 1"
    :options="{ placement: 'bottom-end' }"
    close-on-content-click
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        size="sm"
        :title="t('common.actions.more')"
        data-testid="location-row-menu"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-ellipsis-vertical"
          size="16"
        />
      </RuiButton>
    </template>
    <RuiButton
      v-for="action in available"
      :key="action.key"
      variant="list"
      :color="action.danger ? 'error' : undefined"
      :data-testid="action.testId"
      @click="run(action)"
    >
      <template #prepend>
        <RuiIcon
          :name="action.icon"
          size="16"
        />
      </template>
      {{ action.label }}
    </RuiButton>
  </RuiMenu>
  <div
    v-else
    class="grid grid-cols-4 w-32 justify-items-center"
  >
    <template
      v-for="(action, index) in slots"
      :key="index"
    >
      <RuiButton
        v-if="action"
        variant="text"
        icon
        size="sm"
        :color="action.danger ? 'error' : undefined"
        :title="action.label"
        :aria-label="action.label"
        :data-testid="action.testId"
        @click="run(action)"
      >
        <RuiIcon
          :name="action.icon"
          size="16"
        />
      </RuiButton>
      <div v-else />
    </template>
  </div>
</template>
