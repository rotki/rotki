<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { PremiumDevice } from '@/types/api/premium';
import DateDisplay from '@/components/display/DateDisplay.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import PremiumDeviceFormDialog from '@/components/premium/PremiumDeviceFormDialog.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { usePremiumDevicesApi } from '@/composables/api/premium/devices';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { usePremiumStore } from '@/store/session/premium';

const { t } = useI18n({ useScope: 'global' });

const devices = ref<PremiumDevice[]>([]);
const devicesLimit = ref<number>(0);
const loading = ref<boolean>(false);
const editingDevice = ref<PremiumDevice | undefined>();

const { premium } = storeToRefs(usePremiumStore());

const { deletePremiumDevice, fetchPremiumDevices } = usePremiumDevicesApi();
const { setMessage } = useMessageStore();
const { show } = useConfirmStore();

async function fetchDevices(): Promise<void> {
  set(loading, true);
  try {
    const response = await fetchPremiumDevices();
    set(devices, response.devices);
    set(devicesLimit, response.limit);
  }
  catch (error: any) {
    setMessage({
      description: error.message || error,
      title: t('premium_devices.fetch.error.title'),
    });
  }
  finally {
    set(loading, false);
  }
}

onMounted(async () => {
  if (get(premium)) {
    await fetchDevices();
  }
});

const cols = computed<DataTableColumn<PremiumDevice>[]>(() => [
  {
    key: 'user',
    label: t('premium_devices.table.headers.user'),
    sortable: true,
  },
  {
    key: 'deviceName',
    label: t('premium_devices.table.headers.device_name'),
    sortable: true,
  },
  {
    key: 'platform',
    label: t('premium_devices.table.headers.platform'),
    sortable: true,
  },
  {
    key: 'lastSeenAt',
    label: t('premium_devices.table.headers.last_seen'),
    sortable: true,
  },
  {
    align: 'end',
    cellClass: 'w-[120px]',
    class: 'w-[120px]',
    key: 'actions',
    label: t('common.actions_text'),
    sortable: false,
  },
]);

function edit(device: PremiumDevice): void {
  set(editingDevice, device);
}

function showDeleteConfirmation(device: PremiumDevice): void {
  show(
    {
      message: t('premium_devices.delete.message', { device: device.deviceName }),
      title: t('premium_devices.delete.title'),
    },
    deleteDevice.bind(null, device),
  );
}

async function deleteDevice(device: PremiumDevice): Promise<void> {
  try {
    await deletePremiumDevice(device.deviceIdentifier);
    await fetchDevices();
  }
  catch (error: any) {
    setMessage({
      description: error.message || error,
      title: t('premium_devices.delete.error.title'),
    });
  }
}
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
      <template #item.lastSeenAt="{ row }">
        <DateDisplay :timestamp="row.lastSeenAt" />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          :disabled="loading"
          :delete-tooltip="t('premium_devices.table.actions.delete_tooltip')"
          :edit-tooltip="t('premium_devices.table.actions.edit_tooltip')"
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
