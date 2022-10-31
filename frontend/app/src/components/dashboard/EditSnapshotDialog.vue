<template>
  <v-dialog persistent :value="true" :max-width="1400">
    <v-card elevation="0">
      <v-toolbar dark color="primary">
        <v-btn icon dark @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>

        <v-toolbar-title class="pl-2">
          <i18n path="dashboard.snapshot.edit.dialog.title">
            <template #date>
              <date-display :timestamp="timestamp" />
            </template>
          </i18n>
        </v-toolbar-title>
      </v-toolbar>
      <div v-if="snapshotData">
        <v-stepper v-model="step" elevation="0">
          <v-stepper-header :class="$style.raise">
            <v-stepper-step :step="1">
              {{ tc('dashboard.snapshot.edit.dialog.balances.title') }}
            </v-stepper-step>
            <v-stepper-step :step="2">
              {{ tc('dashboard.snapshot.edit.dialog.location_data.title') }}
            </v-stepper-step>
            <v-stepper-step :step="3">
              {{ tc('common.total') }}
            </v-stepper-step>
          </v-stepper-header>
          <v-stepper-items>
            <v-stepper-content :step="1" class="pa-0">
              <edit-balances-snapshot-table
                v-model="snapshotData"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="save"
              />
            </v-stepper-content>
            <v-stepper-content :step="2" class="pa-0">
              <edit-location-data-snapshot-table
                :value="locationDataSnapshot"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="
                  event => {
                    updateLocationDataSnapshot(event);
                    save();
                  }
                "
              />
            </v-stepper-content>
            <v-stepper-content :step="3" class="pa-0">
              <edit-snapshot-total
                v-if="step === 3"
                :value="locationDataSnapshot"
                :balances-snapshot="balancesSnapshot"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="
                  event => {
                    updateLocationDataSnapshot(event);
                    finish();
                  }
                "
              />
            </v-stepper-content>
          </v-stepper-items>
        </v-stepper>
      </div>
      <div v-else class="d-flex flex-column justify-center align-center py-6">
        <v-progress-circular
          size="50"
          color="primary"
          width="2"
          indeterminate
        />
        <div class="pt-6">
          {{ tc('dashboard.snapshot.edit.dialog.fetch.loading') }}
        </div>
      </div>
    </v-card>
  </v-dialog>
</template>
<script setup lang="ts">
import { ComputedRef, Ref } from 'vue';
import EditBalancesSnapshotTable from '@/components/dashboard/EditBalancesSnapshotTable.vue';
import EditLocationDataSnapshotTable from '@/components/dashboard/EditLocationDataSnapshotTable.vue';
import EditSnapshotTotal from '@/components/dashboard/EditSnapshotTotal.vue';
import { useSnapshotApi } from '@/services/settings/snapshot-api';
import { useMessageStore } from '@/store/message';
import { useNotifications } from '@/store/notifications';
import { useStatisticsStore } from '@/store/statistics';
import {
  BalanceSnapshot,
  LocationDataSnapshot,
  Snapshot,
  SnapshotPayload
} from '@/types/snapshots';
import { sortDesc } from '@/utils/bignumbers';

const props = defineProps({
  timestamp: {
    required: true,
    type: Number
  }
});

const emit = defineEmits(['close', 'finish']);

const { timestamp } = toRefs(props);

const snapshotData: Ref<Snapshot | null> = ref(null);
const step = ref<number>(1);
const { fetchNetValue } = useStatisticsStore();

const api = useSnapshotApi();

const { tc } = useI18n();

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

const { notify } = useNotifications();

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
  if (!data) return false;

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

  let result: boolean = false;

  const notifyError = (e?: any) => {
    notify({
      title: tc('dashboard.snapshot.edit.dialog.message.title'),
      message: tc('dashboard.snapshot.edit.dialog.message.error', 0, {
        message: e
      }),
      display: true
    });
  };

  try {
    result = await api.updateSnapshotData(get(timestamp), payload);

    if (!result) notifyError();
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
      title: tc('dashboard.snapshot.edit.dialog.message.title'),
      description: tc('dashboard.snapshot.edit.dialog.message.success'),
      success: true
    });
    await fetchNetValue();
    emit('finish');
  }
};
</script>
<style module lang="scss">
.asset-select {
  max-width: 640px;
}

.raise {
  position: relative;
  z-index: 2;
}
</style>
