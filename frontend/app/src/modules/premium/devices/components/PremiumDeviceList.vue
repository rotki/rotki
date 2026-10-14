<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { PremiumDevice } from '@/modules/premium/devices/premium';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import PremiumDeviceFormDialog from '@/modules/premium/devices/components/PremiumDeviceFormDialog.vue';
import { usePremiumDevicesApi } from '@/modules/premium/devices/devices';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
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

/** Every slot taken, so signing in on another device needs one removed first. */
const atLimit = computed<boolean>(() => get(devicesLimit) > 0 && get(devices).length >= get(devicesLimit));

// one column for the device, its user and platform under the name, rather than three thin ones
const cols = computed<DataTableColumn<PremiumDevice>[]>(() => [{
  key: 'deviceName',
  label: t('premium_devices.table.headers.device'),
  sortable: true,
}, {
  cellClass: 'whitespace-nowrap',
  key: 'lastSeenAt',
  label: t('premium_devices.table.headers.last_seen'),
  sortable: true,
}, {
  align: 'end',
  key: 'actions',
  label: '',
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
  <TableFrame data-testid="premium-devices">
    <template #toolbar>
      <div class="flex flex-col gap-1 grow min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="m-0 text-base font-semibold text-rui-text">
            {{ t('premium_devices.title') }}
          </h2>
          <RuiChip
            v-if="devicesLimit > 0"
            size="sm"
            variant="tonal"
            :color="atLimit ? 'warning' : 'grey'"
            data-testid="premium-devices-count"
          >
            {{ t('premium_devices.count', { current: devices.length, limit: devicesLimit }) }}
          </RuiChip>
        </div>
        <p class="m-0 text-sm text-rui-text-secondary">
          {{ atLimit ? t('premium_devices.at_limit') : t('premium_devices.description') }}
        </p>
      </div>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            data-testid="premium-devices-refresh"
            @click="fetchDevices()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('premium_devices.refresh') }}
      </RuiTooltip>
    </template>

    <RuiDataTable
      :cols="cols"
      :rows="devices"
      :loading="loading"
      row-attr="deviceIdentifier"
      dense
    >
      <template #item.deviceName="{ row }">
        <div class="flex flex-col gap-0.5 py-1 min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-medium text-rui-text">{{ row.deviceName }}</span>
            <RuiChip
              v-if="row.deviceIdentifier === currentDeviceId"
              size="sm"
              variant="tonal"
              color="primary"
              data-testid="premium-device-current"
            >
              {{ t('premium_devices.table.current_device') }}
            </RuiChip>
          </div>
          <span class="text-sm text-rui-text-secondary">
            {{ t('premium_devices.table.user_platform', { platform: row.platform, user: row.user }) }}
          </span>
        </div>
      </template>
      <template #item.lastSeenAt="{ row }">
        <TimeAgoDisplay :timestamp="row.lastSeenAt" />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          align="end"
          :disabled="loading"
          :delete-disabled="row.deviceIdentifier === currentDeviceId"
          :delete-tooltip="row.deviceIdentifier === currentDeviceId ? t('premium_devices.table.actions.delete_current_tooltip') : t('premium_devices.table.actions.delete_tooltip')"
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
  </TableFrame>
</template>
