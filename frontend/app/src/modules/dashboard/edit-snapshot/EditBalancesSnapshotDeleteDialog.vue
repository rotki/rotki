<script setup lang="ts">
import type { Snapshot } from '@/modules/dashboard/snapshots';
import EditBalancesSnapshotLocationSelector from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotLocationSelector.vue';
import { locationBalanceAfterDelete, type LocationBalancePreview } from '@/modules/dashboard/snapshots/lib/snapshot-location-balance';
import { rebuildSnapshotAfterBalanceChange } from '@/modules/dashboard/snapshots/lib/snapshot-mutations';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

const modelValue = defineModel<Snapshot>({ required: true });

const { index, locations, timestamp } = defineProps<{
  /** Index of the balance to delete, or null when the dialog is closed. */
  index: number | null;
  locations: string[];
  timestamp: number;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const locationToDelete = ref<string>('');

const display = computed<boolean>(() => index !== null);

const previewDeleteLocationBalance = computed<LocationBalancePreview | null>(() => {
  const location = get(locationToDelete);

  if (index === null || !location)
    return null;

  return locationBalanceAfterDelete({ index, location, snapshot: get(modelValue) });
});

watch(() => index, () => {
  set(locationToDelete, '');
});

function confirm(): void {
  if (index === null)
    return;

  const balancesSnapshot = [...get(modelValue).balancesSnapshot];
  balancesSnapshot.splice(index, 1);

  set(modelValue, rebuildSnapshotAfterBalanceChange({
    balancesSnapshot,
    location: get(locationToDelete),
    locationBalance: get(previewDeleteLocationBalance),
    snapshot: get(modelValue),
    timestamp,
  }));

  emit('close');
}
</script>

<template>
  <ConfirmDialog
    :display="display"
    :title="t('dashboard.snapshot.edit.dialog.balances.delete_title')"
    :message="t('dashboard.snapshot.edit.dialog.balances.delete_confirmation')"
    max-width="700"
    @cancel="emit('close')"
    @confirm="confirm()"
  >
    <div class="mt-4">
      <EditBalancesSnapshotLocationSelector
        v-model="locationToDelete"
        :locations="locations"
        :preview-location-balance="previewDeleteLocationBalance"
        :timestamp="timestamp"
      />
    </div>
  </ConfirmDialog>
</template>
