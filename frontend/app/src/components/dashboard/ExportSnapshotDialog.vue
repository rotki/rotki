<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type Message } from '@rotki/common/lib/messages';
import dayjs from 'dayjs';
import { api } from '@/services/rotkehlchen-api';

const props = defineProps({
  value: { required: false, type: Boolean, default: false },
  timestamp: { required: false, type: Number, default: 0 },
  balance: { required: false, type: Number, default: 0 }
});

const emit = defineEmits(['input']);

const { timestamp, balance } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const editMode = ref<boolean>(false);

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

  const url = window.URL.createObjectURL(resp.request.response);

  const date = dayjs(get(timestamp) * 1000).format('YYYYDDMMHHmmss');
  const fileName = `${date}-snapshot.zip`;

  downloadFileByUrl(url, fileName);

  updateVisibility(false);
};

const { setMessage } = useMessageStore();

const { t } = useI18n();

const snapshotApi = useSnapshotApi();
const interop = useInterop();

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

  setMessage(message);
};

const finish = () => {
  updateVisibility(false);
  set(editMode, false);
};

const { show } = useConfirmStore();

const showDeleteConfirmation = () => {
  show(
    {
      title: t('dashboard.snapshot.delete.dialog.title'),
      message: t('dashboard.snapshot.delete.dialog.message')
    },
    deleteSnapshot
  );
};
</script>

<template>
  <VDialog :value="value" max-width="600" @input="updateVisibility($event)">
    <Card>
      <template #title>
        {{ t('dashboard.snapshot.export_database_snapshot') }}
      </template>
      <template #subtitle>
        {{ t('dashboard.snapshot.subtitle') }}
      </template>
      <div class="mb-n2">
        <div>
          <div>{{ t('common.datetime') }}:</div>
          <div class="font-bold">
            <DateDisplay :timestamp="timestamp" />
          </div>
        </div>
        <div class="pt-2">
          <div>{{ t('common.balance') }}:</div>
          <div>
            <AmountDisplay
              :value="formattedSelectedBalance"
              :fiat-currency="currencySymbol"
              class="font-bold"
            />
          </div>
        </div>
      </div>
      <template #buttons>
        <VBtn color="primary" @click="editMode = true">
          <VIcon class="mr-2">mdi-pencil-outline</VIcon>
          {{ t('common.actions.edit') }}
        </VBtn>
        <VBtn color="error" @click="showDeleteConfirmation()">
          <VIcon class="mr-2">mdi-delete-outline</VIcon>
          {{ t('common.actions.delete') }}
        </VBtn>
        <VSpacer />
        <VBtn color="primary" @click="exportSnapshot()">
          <VIcon class="mr-2">mdi-download</VIcon>
          {{ t('common.actions.download') }}
        </VBtn>
      </template>
    </Card>
    <EditSnapshotDialog
      v-if="editMode"
      :timestamp="timestamp"
      @close="editMode = false"
      @finish="finish()"
    />
  </VDialog>
</template>
