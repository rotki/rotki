<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import {
  type BalanceSnapshot,
  type LocationDataSnapshot,
  type Snapshot,
  type SnapshotPayload
} from '@/types/snapshots';

const props = defineProps<{
  timestamp: number;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'finish'): void;
}>();

const { timestamp } = toRefs(props);

const snapshotData: Ref<Snapshot | null> = ref(null);
const step = ref<number>(1);
const { fetchNetValue } = useStatisticsStore();

const api = useSnapshotApi();

const { t } = useI18n();

const balancesSnapshot: ComputedRef<BalanceSnapshot[]> = computed(() => {
  const data = get(snapshotData);
  return !data ? [] : (data.balancesSnapshot as BalanceSnapshot[]);
});

const locationDataSnapshot: ComputedRef<LocationDataSnapshot[]> = computed(
  () => {
    const data = get(snapshotData);
    return !data ? [] : (data.locationDataSnapshot as LocationDataSnapshot[]);
  }
);

const fetchSnapshotData = async () => {
  const result = await api.getSnapshotData(get(timestamp));

  const { balancesSnapshot, locationDataSnapshot } = result;
  balancesSnapshot.sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  locationDataSnapshot.sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  set(snapshotData, {
    balancesSnapshot,
    locationDataSnapshot
  });
};

onMounted(async () => {
  await fetchSnapshotData();
});

const close = () => {
  emit('close');
};

const { notify } = useNotificationsStore();

const updateLocationDataSnapshot = (
  locationDataSnapshot: LocationDataSnapshot[]
) => {
  const data = get(snapshotData);

  const newData = {
    balancesSnapshot: data?.balancesSnapshot || [],
    locationDataSnapshot
  };

  set(snapshotData, newData);
};

const save = async (): Promise<boolean> => {
  const data = get(snapshotData);
  if (!data) {
    return false;
  }

  const payload: SnapshotPayload = {
    balancesSnapshot: [],
    locationDataSnapshot: []
  };

  payload.balancesSnapshot = data.balancesSnapshot.map(item => ({
    ...item,
    amount: item.amount.toFixed(),
    usdValue: item.usdValue.toFixed()
  }));

  payload.locationDataSnapshot = data.locationDataSnapshot.map(item => ({
    ...item,
    usdValue: item.usdValue.toFixed()
  }));

  let result = false;

  const notifyError = (e?: any) => {
    notify({
      title: t('dashboard.snapshot.edit.dialog.message.title'),
      message: t('dashboard.snapshot.edit.dialog.message.error', {
        message: e
      }),
      display: true
    });
  };

  try {
    result = await api.updateSnapshotData(get(timestamp), payload);

    if (!result) {
      notifyError();
    }
  } catch (e: any) {
    notifyError(e);
  }

  if (result) {
    await fetchSnapshotData();
  }

  return result;
};

const { setMessage } = useMessageStore();

const finish = async () => {
  const success = await save();

  if (success) {
    setMessage({
      title: t('dashboard.snapshot.edit.dialog.message.title'),
      description: t('dashboard.snapshot.edit.dialog.message.success'),
      success: true
    });
    await fetchNetValue();
    emit('finish');
  }
};

const updateAndSave = (event: LocationDataSnapshot[]) => {
  updateLocationDataSnapshot(event);
  save();
};

const updateAndComplete = (event: LocationDataSnapshot[]) => {
  updateLocationDataSnapshot(event);
  finish();
};
</script>

<template>
  <VDialog persistent :value="true" :max-width="1400">
    <VCard elevation="0">
      <VToolbar dark color="primary">
        <VBtn icon dark @click="close()">
          <VIcon>mdi-close</VIcon>
        </VBtn>

        <VToolbarTitle class="pl-2">
          <i18n path="dashboard.snapshot.edit.dialog.title">
            <template #date>
              <DateDisplay :timestamp="timestamp" />
            </template>
          </i18n>
        </VToolbarTitle>
      </VToolbar>
      <div v-if="snapshotData">
        <VStepper v-model="step" elevation="0">
          <VStepperHeader :class="$style.raise">
            <VStepperStep :step="1">
              {{ t('dashboard.snapshot.edit.dialog.balances.title') }}
            </VStepperStep>
            <VStepperStep :step="2">
              {{ t('dashboard.snapshot.edit.dialog.location_data.title') }}
            </VStepperStep>
            <VStepperStep :step="3">
              {{ t('common.total') }}
            </VStepperStep>
          </VStepperHeader>
          <VStepperItems>
            <VStepperContent :step="1" class="pa-0">
              <EditBalancesSnapshotTable
                v-model="snapshotData"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="save()"
              />
            </VStepperContent>
            <VStepperContent :step="2" class="pa-0">
              <EditLocationDataSnapshotTable
                :value="locationDataSnapshot"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="updateAndSave($event)"
              />
            </VStepperContent>
            <VStepperContent :step="3" class="pa-0">
              <EditSnapshotTotal
                v-if="step === 3"
                :value="locationDataSnapshot"
                :balances-snapshot="balancesSnapshot"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="updateAndComplete($event)"
              />
            </VStepperContent>
          </VStepperItems>
        </VStepper>
      </div>
      <div v-else class="flex flex-col justify-center items-center py-6">
        <VProgressCircular size="50" color="primary" width="2" indeterminate />
        <div class="pt-6">
          {{ t('dashboard.snapshot.edit.dialog.fetch.loading') }}
        </div>
      </div>
    </VCard>
  </VDialog>
</template>

<style module lang="scss">
.asset-select {
  max-width: 640px;
}

.raise {
  position: relative;
  z-index: 2;
}
</style>
