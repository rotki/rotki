<script setup lang="ts">
import type { Snapshot } from '@/modules/dashboard/snapshots';
import type { IndexedBalanceSnapshot } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-rows';
import type { BalanceDeletion } from '@/modules/dashboard/snapshots/composables/use-snapshot-draft';
import type { BalanceMutation } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { get } from '@vueuse/shared';
import { useTemplateRef } from 'vue';
import SnapshotBalanceDeleteDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceDeleteDialog.vue';
import SnapshotBalanceEntryDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceEntryDialog.vue';

const { snapshot, timestamp } = defineProps<{
  snapshot: Snapshot;
  timestamp: number;
}>();

const emit = defineEmits<{
  add: [mutation: BalanceMutation];
  edit: [payload: { index: number; mutation: BalanceMutation }];
  delete: [payload: BalanceDeletion];
}>();

const entryDialog = useTemplateRef<InstanceType<typeof SnapshotBalanceEntryDialog>>('entryDialog');
const deleteDialog = useTemplateRef<InstanceType<typeof SnapshotBalanceDeleteDialog>>('deleteDialog');

/** Both dialogs render unconditionally, so a missing one is a bug rather than a state to skip. */
function mounted<T>(dialog: T | null, name: string): T {
  if (!dialog)
    throw new Error(`${name} is not mounted`);
  return dialog;
}

function openAdd(): void {
  mounted(get(entryDialog), 'entryDialog').openAdd();
}

function openEdit(item: IndexedBalanceSnapshot): void {
  mounted(get(entryDialog), 'entryDialog').openEdit(item);
}

function openDelete(item: IndexedBalanceSnapshot): void {
  mounted(get(deleteDialog), 'deleteDialog').open(item.index);
}

function onSubmit(payload: { index: number | null; mutation: BalanceMutation }): void {
  if (payload.index === null)
    emit('add', payload.mutation);
  else
    emit('edit', { index: payload.index, mutation: payload.mutation });
}

function onDelete(payload: BalanceDeletion): void {
  emit('delete', payload);
}

defineExpose({ openAdd, openDelete, openEdit });
</script>

<template>
  <SnapshotBalanceEntryDialog
    ref="entryDialog"
    :snapshot="snapshot"
    :timestamp="timestamp"
    @submit="onSubmit($event)"
  />

  <SnapshotBalanceDeleteDialog
    ref="deleteDialog"
    :snapshot="snapshot"
    :timestamp="timestamp"
    @confirm="onDelete($event)"
  />
</template>
