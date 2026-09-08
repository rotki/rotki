<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { PremiumDevice } from '@/modules/premium/devices/premium';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import PremiumDeviceFormDialog from '@/modules/premium/devices/components/PremiumDeviceFormDialog.vue';
import { usePremiumDevicesApi } from '@/modules/premium/devices/devices';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import RefreshButton from '@/modules/shell/components/RefreshButton.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { t } = useI18n({ useScope: 'global' });

const devices = ref<PremiumDevice[]>([]);
const devicesLimit = ref<number>(0);
const loading = ref<boolean>(false);
const editingDevice = ref<PremiumDevice>();
const currentDeviceId = ref<string>();

const { premium } = storeToRefs(usePremiumStore());

const { deletePremiumDevice, fetchPremiumDevices } = usePremiumDevicesApi();
const { setMessage } = useMessageStore();

const cols = computed<DataTableColumn<PremiumDevice>[]>(() => [{
  key: 'deviceName',
  label: t('premium_devices.table.headers.device_name'),
  sortable: true,
}, {
  key: 'currentIndicator',
  label: '',
  sortable: false,
}, {
  key: 'platform',
  label: t('premium_devices.table.headers.platform'),
  sortable: true,
}, {
  key: 'user',
  label: t('premium_devices.table.headers.user'),
  sortable: true,
}, {
  key: 'lastSeenAt',
  label: t('premium_devices.table.headers.last_seen'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'w-[120px]',
  class: 'w-[120px]',
  key: 'actions',
  label: t('common.actions_text'),
  sortable: false,
}]);

async function fetchDevices(): Promise<void> {
  set(loading, true);
  try {
    const response = await fetchPremiumDevices();
    set(devices, response.devices);
    set(devicesLimit, response.limit);
    set(currentDeviceId, response.currentDeviceId);
  }
  catch (error: unknown) {
    setMessage({
      description: getErrorMessage(error),
      title: t('premium_devices.fetch.error.title'),
    });
  }
  finally {
    set(loading, false);
  }
}

function edit(device: PremiumDevice): void {
  set(editingDevice, device);
}

const { showDeleteConfirmation } = useTableRowDeletion<PremiumDevice>({
  confirm: device => ({
    message: t('premium_devices.delete.message', { device: device.deviceName }),
    title: t('premium_devices.delete.title'),
  }),
  deleteItem: async device => deletePremiumDevice(device.deviceIdentifier),
  errorMessage: (_device, error) => ({
    description: getErrorMessage(error),
    title: t('premium_devices.delete.error.title'),
  }),
  onDeleted: fetchDevices,
});

onMounted(async () => {
  if (get(premium)) {
    await fetchDevices();
  }
});
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex items-center gap-2 p-4">
        <RefreshButton
          :loading="loading"
          :tooltip="t('premium_devices.refresh')"
          @refresh="fetchDevices()"
        />
        <div>
          <CardTitle>
            {{ t('premium_devices.title') }}
          </CardTitle>
          <div class="text-rui-text-secondary text-sm">
            {{ t('premium_devices.limit', { current: devices.length, limit: devicesLimit }) }}
          </div>
        </div>
      </div>
    </template>

    <RuiDataTable
      :cols="cols"
      :rows="devices"
      :loading="loading"
      row-attr="deviceIdentifier"
      outlined
    >
      <template #item.currentIndicator="{ row }">
        <RuiChip
          v-if="row.deviceIdentifier === currentDeviceId"
          size="sm"
          color="success"
        >
          {{ t('premium_devices.table.current_device') }}
        </RuiChip>
      </template>
      <template #item.lastSeenAt="{ row }">
        <DateDisplay :timestamp="row.lastSeenAt" />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          :disabled="loading"
          :delete-tooltip="t('premium_devices.table.actions.delete_tooltip')"
          :edit-tooltip="t('premium_devices.table.actions.edit_tooltip')"
          :delete-disabled="row.deviceIdentifier === currentDeviceId"
          @delete-click="showDeleteConfirmation(row)"
          @edit-click="edit(row)"
        />
      </template>
    </RuiDataTable>

    <PremiumDeviceFormDialog
      v-model="editingDevice"
      @refresh="fetchDevices()"
    />
  </RuiCard>
</template>
