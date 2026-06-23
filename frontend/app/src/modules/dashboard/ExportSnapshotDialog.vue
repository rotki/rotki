<script setup lang="ts">
import type { BigNumber, Message } from '@rotki/common';
import dayjs from 'dayjs';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { downloadFileByBlob } from '@/modules/core/common/file/download';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const display = defineModel<boolean>({ default: false, required: true });

const { balance, loading = false, timestamp = 0 } = defineProps<{
  balance: BigNumber;
  loading?: boolean;
  timestamp?: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const { setMessage } = useMessageStore();
const snapshotApi = useSnapshotApi();
const { appSession, openDirectory } = useInterop();

async function downloadSnapshot() {
  const response = await snapshotApi.downloadSnapshot(timestamp);

  const date = dayjs(timestamp * 1000).format('YYYYDDMMHHmmss');
  const fileName = `${date}-snapshot.zip`;

  downloadFileByBlob(response, fileName);

  set(display, false);
}

async function exportSnapshotCSV() {
  let message: Message | null = null;

  try {
    if (appSession) {
      const path = await openDirectory(t('common.select_directory'));

      if (!path)
        return;

      const success = await snapshotApi.exportSnapshotCSV({
        path,
        timestamp,
      });

      message = {
        description: success
          ? t('dashboard.snapshot.download.message.success')
          : t('dashboard.snapshot.download.message.failure'),
        success,
        title: t('dashboard.snapshot.download.message.title'),
      };

      set(display, false);
    }
    else {
      await downloadSnapshot();
    }
  }
  catch (error: unknown) {
    message = {
      description: getErrorMessage(error),
      success: false,
      title: t('dashboard.snapshot.download.message.title'),
    };
  }

  if (message)
    setMessage(message);
}

async function exportSnapshot() {
  if (appSession)
    await exportSnapshotCSV();
  else await downloadSnapshot();
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
        <RuiSkeletonLoader
          v-if="loading"
          class="w-24 h-5"
        />
        <FiatDisplay
          v-else-if="balance"
          :value="balance"
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
          data-testid="export-snapshot-download"
          @click="exportSnapshot()"
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
