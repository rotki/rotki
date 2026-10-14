<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import { useSnapshotExport } from '@/modules/dashboard/snapshots/composables/use-snapshot-export';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const display = defineModel<boolean>({ default: false, required: true });

const { balance, timestamp = 0 } = defineProps<{
  /** The snapshot's net worth, denominated in USD (converted for display here). */
  balance: BigNumber;
  /** The snapshot timestamp in seconds, used for the historic USD-to-fiat rate. */
  timestamp?: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const { exporting, exportSnapshot } = useSnapshotExport();

async function download(): Promise<void> {
  if (await exportSnapshot(timestamp))
    set(display, false);
}
</script>

<template>
  <RuiDialog
    v-model="display"
    max-width="600"
  >
    <RuiCard data-testid="export-snapshot-dialog">
      <template #header>
        {{ t('dashboard.snapshot.export_database_snapshot') }}
      </template>
      <template #subheader>
        {{ t('dashboard.snapshot.subtitle') }}
      </template>
      <div class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2">
        <div class="text-rui-text-secondary">
          {{ t('common.datetime') }}
        </div>
        <DateDisplay
          :timestamp="timestamp"
          class="font-bold"
        />
        <div class="text-rui-text-secondary">
          {{ t('common.balance') }}
        </div>
        <SnapshotFiatDisplay
          v-if="balance"
          :value="balance"
          :timestamp="timestamp"
          class="font-bold"
        />
      </div>
      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          data-testid="export-snapshot-cancel"
          @click="display = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :loading="exporting === timestamp"
          data-testid="export-snapshot-download"
          @click="download()"
        >
          <template #prepend>
            <RuiIcon name="lu-file-down" />
          </template>
          {{ t('common.actions.download') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
