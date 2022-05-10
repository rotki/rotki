<template>
  <v-dialog :value="value" max-width="600" @input="updateVisibility">
    <card>
      <template #title>
        {{ $t('dashboard.snapshot.export_database_snapshot') }}
      </template>
      <template #subtitle>
        {{ $t('dashboard.snapshot.subtitle') }}
      </template>
      <div class="mb-n4">
        <div>
          <div>
            {{ $t('dashboard.snapshot.time') }}
          </div>
          <div>
            <date-display class="font-weight-bold" :timestamp="timestamp" />
          </div>
        </div>
        <div class="pt-2">
          <div>
            {{ $t('dashboard.snapshot.balance') }}
          </div>
          <div>
            <amount-display
              :value="formattedSelectedBalance"
              :fiat-currency="currency.tickerSymbol"
              class="font-weight-bold"
            />
          </div>
        </div>
      </div>
      <template #buttons>
        <v-spacer />
        <v-btn color="error" @click="deleteSnapshotConfirmationDialog = true">
          <v-icon class="mr-2">mdi-delete-outline</v-icon>
          {{ $t('dashboard.snapshot.delete_snapshot') }}
        </v-btn>
        <v-btn depressed color="primary" @click="exportSnapshot">
          <v-icon class="mr-2">mdi-download</v-icon>
          {{ $t('dashboard.snapshot.download_snapshot') }}
        </v-btn>
      </template>
    </card>
    <confirm-dialog
      v-if="deleteSnapshotConfirmationDialog"
      display
      :title="$tc('dashboard.snapshot.delete_dialog.title')"
      :message="$tc('dashboard.snapshot.delete_dialog.message')"
      @cancel="deleteSnapshotConfirmationDialog = false"
      @confirm="deleteSnapshot"
    />
  </v-dialog>
</template>
<script lang="ts">
import { BigNumber } from '@rotki/common';
import { Message } from '@rotki/common/lib/messages';
import { computed, defineComponent, ref, toRefs } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import dayjs from 'dayjs';
import { setupGeneralSettings } from '@/composables/session';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/store';
import { useStore } from '@/store/utils';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { downloadFileByUrl } from '@/utils/download';

export default defineComponent({
  name: 'ExportSnapshotDialog',
  props: {
    value: { required: false, type: Boolean, default: false },
    timestamp: { required: false, type: Number, default: 0 },
    balance: { required: false, type: Number, default: 0 }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { timestamp, balance } = toRefs(props);
    const { currency } = setupGeneralSettings();

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
      const resp = await api.downloadSnapshot({
        timestamp: get(timestamp)
      });

      const blob = new Blob([resp.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);

      const date = dayjs(get(timestamp) * 1000).format('YYYYDDMMHHmmss');
      const fileName = `${date}-snapshot.zip`;

      downloadFileByUrl(url, fileName);

      updateVisibility(false);
    };

    const { setMessage } = useMainStore();

    const exportSnapshotCSV = async () => {
      let message: Message | null = null;

      try {
        if (interop.isPackaged && api.defaultBackend) {
          const path = await interop.openDirectory(
            i18n.t('dashboard.snapshot.select_directory').toString()
          );

          if (!path) {
            return;
          }

          const success = await api.exportSnapshotCSV({
            path,
            timestamp: get(timestamp)
          });

          message = {
            title: i18n.t('dashboard.snapshot.message.title').toString(),
            description: success
              ? i18n.t('dashboard.snapshot.message.success').toString()
              : i18n.t('dashboard.snapshot.message.failure').toString(),
            success
          };

          updateVisibility(false);
        } else {
          await downloadSnapshot();
        }
      } catch (e: any) {
        message = {
          title: i18n.t('dashboard.snapshot.message.title').toString(),
          description: e.message,
          success: false
        };
      }

      if (message) {
        setMessage(message);
      }
    };

    const exportSnapshot = () => {
      if (interop.isPackaged) {
        exportSnapshotCSV();
      } else {
        downloadSnapshot();
      }
    };

    const deleteSnapshot = async () => {
      let message: Message | null;

      try {
        const success = await api.deleteSnapshot({
          timestamp: get(timestamp)
        });

        message = {
          title: i18n.t('dashboard.snapshot.delete_message.title').toString(),
          description: success
            ? i18n.t('dashboard.snapshot.delete_message.success').toString()
            : i18n.t('dashboard.snapshot.delete_message.failure').toString(),
          success
        };

        updateVisibility(false);

        const store = useStore();
        store.dispatch('statistics/fetchNetValue');
      } catch (e: any) {
        message = {
          title: i18n.t('dashboard.snapshot.message.title').toString(),
          description: e.message,
          success: false
        };
      }

      set(deleteSnapshotConfirmationDialog, false);

      setMessage(message);
    };

    return {
      currency,
      formattedSelectedBalance,
      updateVisibility,
      exportSnapshot,
      deleteSnapshotConfirmationDialog,
      deleteSnapshot
    };
  }
});
</script>
