<template>
  <v-dialog :value="value" max-width="600" @input="updateVisibility">
    <card>
      <template #title>
        {{ t('dashboard.snapshot.export_database_snapshot') }}
      </template>
      <template #subtitle>
        {{ t('dashboard.snapshot.subtitle') }}
      </template>
      <div class="mb-n2">
        <div>
          <div>{{ t('common.datetime') }}:</div>
          <div>
            <date-display class="font-weight-bold" :timestamp="timestamp" />
          </div>
        </div>
        <div class="pt-2">
          <div>{{ t('common.balance') }}:</div>
          <div>
            <amount-display
              :value="formattedSelectedBalance"
              :fiat-currency="currencySymbol"
              class="font-weight-bold"
            />
          </div>
        </div>
      </div>
      <template #buttons>
        <v-btn color="primary" @click="editMode = true">
          <v-icon class="mr-2">mdi-pencil-outline</v-icon>
          {{ t('common.actions.edit') }}
        </v-btn>
        <v-btn color="error" @click="deleteSnapshotConfirmationDialog = true">
          <v-icon class="mr-2">mdi-delete-outline</v-icon>
          {{ t('common.actions.delete') }}
        </v-btn>
        <v-spacer />
        <v-btn color="primary" @click="exportSnapshot">
          <v-icon class="mr-2">mdi-download</v-icon>
          {{ t('common.actions.download') }}
        </v-btn>
      </template>
    </card>
    <confirm-dialog
      v-if="deleteSnapshotConfirmationDialog"
      display
      :title="tc('dashboard.snapshot.delete.dialog.title')"
      :message="tc('dashboard.snapshot.delete.dialog.message')"
      @cancel="deleteSnapshotConfirmationDialog = false"
      @confirm="deleteSnapshot"
    />
    <edit-snapshot-dialog
      v-if="editMode"
      :timestamp="timestamp"
      @close="editMode = false"
      @finish="finish"
    />
  </v-dialog>
</template>
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { Message } from '@rotki/common/lib/messages';
import dayjs from 'dayjs';
import EditSnapshotDialog from '@/components/dashboard/EditSnapshotDialog.vue';
import { interop } from '@/electron-interop';
import { api } from '@/services/rotkehlchen-api';
import { useSnapshotApi } from '@/services/settings/snapshot-api';
import { useMessageStore } from '@/store/message';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { downloadFileByUrl } from '@/utils/download';

const props = defineProps({
  value: { required: false, type: Boolean, default: false },
  timestamp: { required: false, type: Number, default: 0 },
  balance: { required: false, type: Number, default: 0 }
});

const emit = defineEmits(['input']);

const { timestamp, balance } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const editMode = ref<boolean>(false);

const deleteSnapshotConfirmationDialog = ref<boolean>(false);

const updateVisibility = (visible: boolean) => {
  emit('input', visible);
};

const formattedSelectedBalance = computed<BigNumber | null>(() => {
  if (get(balance)) {
    return get(bigNumberifyFromRef(balance));
  }

  return null;
});

const downloadSnapshot = async () => {
  const resp = await snapshotApi.downloadSnapshot(get(timestamp));

  const blob = new Blob([resp.data], { type: 'application/zip' });
  const url = window.URL.createObjectURL(blob);

  const date = dayjs(get(timestamp) * 1000).format('YYYYDDMMHHmmss');
  const fileName = `${date}-snapshot.zip`;

  downloadFileByUrl(url, fileName);

  updateVisibility(false);
};

const { setMessage } = useMessageStore();

const { t, tc } = useI18n();

const snapshotApi = useSnapshotApi();

const exportSnapshotCSV = async () => {
  let message: Message | null = null;

  try {
    if (interop.isPackaged && api.defaultBackend) {
      const path = await interop.openDirectory(
        t('dashboard.snapshot.select_directory').toString()
      );

      if (!path) {
        return;
      }

      const success = await snapshotApi.exportSnapshotCSV({
        path,
        timestamp: get(timestamp)
      });

      message = {
        title: t('dashboard.snapshot.download.message.title').toString(),
        description: success
          ? t('dashboard.snapshot.download.message.success').toString()
          : t('dashboard.snapshot.download.message.failure').toString(),
        success
      };

      updateVisibility(false);
    } else {
      await downloadSnapshot();
    }
  } catch (e: any) {
    message = {
      title: t('dashboard.snapshot.download.message.title').toString(),
      description: e.message,
      success: false
    };
  }

  if (message) {
    setMessage(message);
  }
};

const exportSnapshot = async () => {
  if (interop.isPackaged) {
    await exportSnapshotCSV();
  } else {
    await downloadSnapshot();
  }
};

const { fetchNetValue } = useStatisticsStore();

const deleteSnapshot = async () => {
  let message: Message | null;

  try {
    const success = await snapshotApi.deleteSnapshot({
      timestamp: get(timestamp)
    });

    message = {
      title: t('dashboard.snapshot.delete.message.title').toString(),
      description: success
        ? t('dashboard.snapshot.delete.message.success').toString()
        : t('dashboard.snapshot.delete.message.failure').toString(),
      success
    };

    updateVisibility(false);
    await fetchNetValue();
  } catch (e: any) {
    message = {
      title: t('dashboard.snapshot.download.message.title').toString(),
      description: e.message,
      success: false
    };
  }

  set(deleteSnapshotConfirmationDialog, false);

  setMessage(message);
};

const finish = () => {
  updateVisibility(false);
  set(editMode, false);
};
</script>
