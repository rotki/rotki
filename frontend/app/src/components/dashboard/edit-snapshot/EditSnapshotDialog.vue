<script setup lang="ts">
import type { BalanceSnapshot, LocationDataSnapshot, Snapshot, SnapshotPayload } from '@/types/snapshots';
import EditBalancesSnapshotTable from '@/components/dashboard/edit-snapshot/EditBalancesSnapshotTable.vue';
import EditLocationDataSnapshotTable from '@/components/dashboard/edit-snapshot/EditLocationDataSnapshotTable.vue';
import EditSnapshotTotal from '@/components/dashboard/edit-snapshot/EditSnapshotTotal.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useSnapshotApi } from '@/composables/api/settings/snapshot-api';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useStatisticsStore } from '@/store/statistics';
import { sortDesc } from '@/utils/bignumbers';

const props = defineProps<{
  timestamp: number;
}>();

const emit = defineEmits<{
  close: [];
  finish: [];
}>();

const { timestamp } = toRefs(props);

const snapshotData = ref<Snapshot | null>(null);
const step = ref<number>(1);
const { fetchNetValue } = useStatisticsStore();

const api = useSnapshotApi();

const { t } = useI18n({ useScope: 'global' });

const balancesSnapshot = computed<BalanceSnapshot[]>(() => {
  const data = get(snapshotData);
  return !data ? [] : (data.balancesSnapshot as BalanceSnapshot[]);
});

const locationDataSnapshot = computed<LocationDataSnapshot[]>(() => {
  const data = get(snapshotData);
  return !data ? [] : (data.locationDataSnapshot as LocationDataSnapshot[]);
});

async function fetchSnapshotData() {
  const result = await api.getSnapshotData(get(timestamp));

  const { balancesSnapshot, locationDataSnapshot } = result;
  balancesSnapshot.sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  locationDataSnapshot.sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  set(snapshotData, {
    balancesSnapshot,
    locationDataSnapshot,
  });
}

onMounted(async () => {
  await fetchSnapshotData();
});

function close() {
  emit('close');
}

const { notify } = useNotificationsStore();

function updateLocationDataSnapshot(locationDataSnapshot: LocationDataSnapshot[]) {
  const data = get(snapshotData);

  const newData = {
    balancesSnapshot: data?.balancesSnapshot || [],
    locationDataSnapshot,
  };

  set(snapshotData, newData);
}

async function save(): Promise<boolean> {
  const data = get(snapshotData);
  if (!data)
    return false;

  const payload: SnapshotPayload = {
    balancesSnapshot: [],
    locationDataSnapshot: [],
  };

  payload.balancesSnapshot = data.balancesSnapshot.map(item => ({
    ...item,
    amount: item.amount.toFixed(),
    usdValue: item.usdValue.toFixed(),
  }));

  payload.locationDataSnapshot = data.locationDataSnapshot.map(item => ({
    ...item,
    usdValue: item.usdValue.toFixed(),
  }));

  let result = false;

  const notifyError = (e?: any) => {
    notify({
      display: true,
      message: t('dashboard.snapshot.edit.dialog.message.error', {
        message: e,
      }),
      title: t('dashboard.snapshot.edit.dialog.message.title'),
    });
  };

  try {
    result = await api.updateSnapshotData(get(timestamp), payload);

    if (!result)
      notifyError();
  }
  catch (error: any) {
    notifyError(error);
  }

  if (result)
    await fetchSnapshotData();

  return result;
}

const { setMessage } = useMessageStore();

async function finish() {
  const success = await save();

  if (success) {
    setMessage({
      description: t('dashboard.snapshot.edit.dialog.message.success'),
      success: true,
      title: t('dashboard.snapshot.edit.dialog.message.title'),
    });
    await fetchNetValue();
    emit('finish');
  }
}

function updateAndSave(event: LocationDataSnapshot[]) {
  updateLocationDataSnapshot(event);
  save();
}

function updateAndComplete(event: LocationDataSnapshot[]) {
  updateLocationDataSnapshot(event);
  finish();
}

const steps = computed(() => [
  {
    title: t('dashboard.snapshot.edit.dialog.balances.title'),
  },
  {
    title: t('dashboard.snapshot.edit.dialog.location_data.title'),
  },
  {
    title: t('common.total'),
  },
]);
</script>

<template>
  <RuiDialog
    persistent
    :model-value="true"
    max-width="1400"
  >
    <RuiCard
      no-padding
      variant="flat"
      class="overflow-hidden"
    >
      <div class="flex bg-rui-primary text-white p-2">
        <RuiButton
          variant="text"
          icon
          @click="close()"
        >
          <RuiIcon
            class="text-white"
            name="lu-x"
          />
        </RuiButton>

        <h5 class="pl-2 text-h5 flex items-center">
          <i18n-t
            scope="global"
            keypath="dashboard.snapshot.edit.dialog.title"
            tag="span"
          >
            <template #date>
              <DateDisplay :timestamp="timestamp" />
            </template>
          </i18n-t>
        </h5>
      </div>

      <div v-if="snapshotData">
        <RuiStepper
          :steps="steps"
          :step="step"
          class="py-4 border-b-2 border-default"
        />
        <RuiTabItems v-model="step">
          <RuiTabItem :value="1">
            <EditBalancesSnapshotTable
              v-model="snapshotData"
              :timestamp="timestamp"
              @update:step="step = $event"
              @update:model-value="save()"
            />
          </RuiTabItem>
          <RuiTabItem :value="2">
            <EditLocationDataSnapshotTable
              :model-value="locationDataSnapshot"
              :timestamp="timestamp"
              @update:step="step = $event"
              @update:model-value="updateAndSave($event)"
            />
          </RuiTabItem>
          <RuiTabItem :value="3">
            <EditSnapshotTotal
              :model-value="locationDataSnapshot"
              :balances-snapshot="balancesSnapshot"
              :timestamp="timestamp"
              @update:step="step = $event"
              @update:model-value="updateAndComplete($event)"
            />
          </RuiTabItem>
        </RuiTabItems>
      </div>
      <div
        v-else
        class="flex flex-col justify-center items-center py-6 bg-white dark:bg-rui-grey-800"
      >
        <RuiProgress
          circular
          variant="indeterminate"
          color="primary"
          size="50"
        />

        <div class="pt-6">
          {{ t('dashboard.snapshot.edit.dialog.fetch.loading') }}
        </div>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
