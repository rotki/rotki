<script setup lang="ts">
import type { SnapshotChange } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import SnapshotChangesList from '@/modules/dashboard/snapshots/components/SnapshotChangesList.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const {
  canUndo = false,
  changes,
  hasNext = false,
  hasPrev = false,
  saving = false,
} = defineProps<{
  /** Snapshot timestamp, in seconds. */
  timestamp: number;
  /** The structured change list; dirtiness and the count derive from it. */
  changes: SnapshotChange[];
  canUndo?: boolean;
  saving?: boolean;
  hasPrev?: boolean;
  hasNext?: boolean;
}>();

const emit = defineEmits<{
  save: [];
  discard: [];
  undo: [];
  export: [];
  delete: [];
  navigate: [direction: 'prev' | 'next'];
}>();

const { t } = useI18n({ useScope: 'global' });

const overflowOpen = ref<boolean>(false);
const reviewOpen = ref<boolean>(false);

const isDirty = computed<boolean>(() => changes.length > 0);
const dirtyCount = computed<number>(() => changes.length);

function exportSnapshot(): void {
  set(overflowOpen, false);
  emit('export');
}

function deleteSnapshot(): void {
  set(overflowOpen, false);
  emit('delete');
}
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-4 min-h-9">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
      <nav class="flex items-center text-sm font-medium">
        <span class="text-rui-text-secondary">{{ t('navigation_menu.statistics') }}</span>
        <RuiIcon
          name="lu-chevron-right"
          size="16"
          class="mx-2 text-rui-text-secondary"
        />
        <RouterLink
          :to="{ name: '/statistics/snapshots/' }"
          class="text-rui-text-secondary hover:text-rui-text"
          data-testid="snapshot-breadcrumb-list"
        >
          {{ t('dashboard.snapshot.list.title') }}
        </RouterLink>
        <RuiIcon
          name="lu-chevron-right"
          size="16"
          class="mx-2 text-rui-text-secondary"
        />
        <h1 class="text-sm font-medium text-rui-text">
          <DateDisplay :timestamp="timestamp" />
        </h1>
      </nav>

      <div class="flex">
        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="text"
              icon
              size="sm"
              :disabled="!hasPrev"
              data-testid="snapshot-nav-prev"
              @click="emit('navigate', 'prev')"
            >
              <RuiIcon name="lu-chevron-left" />
            </RuiButton>
          </template>
          {{ t('dashboard.snapshot.detail.navigation.previous') }}
        </RuiTooltip>
        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="text"
              icon
              size="sm"
              :disabled="!hasNext"
              data-testid="snapshot-nav-next"
              @click="emit('navigate', 'next')"
            >
              <RuiIcon name="lu-chevron-right" />
            </RuiButton>
          </template>
          {{ t('dashboard.snapshot.detail.navigation.next') }}
        </RuiTooltip>
      </div>

      <RuiMenu
        v-if="isDirty"
        v-model="reviewOpen"
        :options="{ placement: 'bottom-start' }"
      >
        <template #activator="{ attrs }">
          <RuiChip
            size="sm"
            color="warning"
            clickable
            data-testid="snapshot-dirty-badge"
            v-bind="attrs"
          >
            {{ t('dashboard.snapshot.detail.unsaved_changes', dirtyCount) }}
          </RuiChip>
        </template>
        <div class="p-4 max-w-96">
          <div class="text-subtitle-2 mb-2">
            {{ t('dashboard.snapshot.detail.changes.title') }}
          </div>
          <SnapshotChangesList
            :changes="changes"
            :timestamp="timestamp"
          />
        </div>
      </RuiMenu>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <RuiButton
        variant="text"
        :disabled="!canUndo"
        data-testid="snapshot-undo"
        @click="emit('undo')"
      >
        <template #prepend>
          <RuiIcon name="lu-undo-2" />
        </template>
        {{ t('common.actions.undo') }}
      </RuiButton>
      <RuiButton
        variant="text"
        :disabled="!isDirty"
        data-testid="snapshot-discard"
        @click="emit('discard')"
      >
        {{ t('common.actions.discard') }}
      </RuiButton>
      <RuiButton
        color="primary"
        :disabled="!isDirty"
        :loading="saving"
        data-testid="snapshot-save"
        @click="emit('save')"
      >
        <template #prepend>
          <RuiIcon name="lu-save" />
        </template>
        {{ t('common.actions.save') }}
      </RuiButton>

      <RuiMenu
        v-model="overflowOpen"
        :options="{ placement: 'bottom-end' }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="sm"
            data-testid="snapshot-overflow"
            v-bind="attrs"
          >
            <RuiIcon name="lu-ellipsis-vertical" />
          </RuiButton>
        </template>
        <div class="py-1">
          <RuiButton
            variant="list"
            data-testid="snapshot-export"
            @click="exportSnapshot()"
          >
            <template #prepend>
              <RuiIcon name="lu-download" />
            </template>
            {{ t('common.actions.export') }}
          </RuiButton>
          <RuiButton
            variant="list"
            data-testid="snapshot-delete"
            @click="deleteSnapshot()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-trash-2"
                color="error"
              />
            </template>
            {{ t('common.actions.delete') }}
          </RuiButton>
        </div>
      </RuiMenu>
    </div>
  </div>
</template>
