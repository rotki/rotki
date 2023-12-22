<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { StepperState } from '@rotki/ui-library-compat';
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

const steps = computed(() => {
  const stepVal = get(step);
  return [
    {
      title: t('dashboard.snapshot.edit.dialog.balances.title'),
      state: stepVal > 0 ? StepperState.active : StepperState.inactive
    },
    {
      title: t('dashboard.snapshot.edit.dialog.location_data.title'),
      state: stepVal > 1 ? StepperState.active : StepperState.inactive
    },
    {
      title: t('common.total'),
      state: stepVal > 2 ? StepperState.active : StepperState.inactive
    }
  ];
});
</script>

<template>
  <VDialog persistent :value="true" max-width="1400">
    <RuiCard no-padding variant="flat">
      <div class="flex bg-rui-primary text-white p-2">
        <RuiButton variant="text" icon @click="close()">
          <RuiIcon class="text-white" name="close-line" />
        </RuiButton>

        <h5 class="pl-2 text-h5 flex items-center">
          <i18n path="dashboard.snapshot.edit.dialog.title">
            <template #date>
              <DateDisplay :timestamp="timestamp" />
            </template>
          </i18n>
        </h5>
      </div>

      <div v-if="snapshotData">
        <RuiStepper :steps="steps" class="py-4 border-b-2 border-default" />
        <RuiTabItems v-model="step">
          <template #default>
            <RuiTabItem :value="1">
              <EditBalancesSnapshotTable
                v-model="snapshotData"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="save()"
              />
            </RuiTabItem>
            <RuiTabItem :value="2">
              <EditLocationDataSnapshotTable
                :value="locationDataSnapshot"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="updateAndSave($event)"
              />
            </RuiTabItem>
            <RuiTabItem :value="3">
              <EditSnapshotTotal
                v-if="step === 3"
                :value="locationDataSnapshot"
                :balances-snapshot="balancesSnapshot"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="updateAndComplete($event)"
              />
            </RuiTabItem>
          </template>
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
