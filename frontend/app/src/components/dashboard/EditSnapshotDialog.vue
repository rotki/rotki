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
              {{ $t('dashboard.snapshot.edit.dialog.balances.title') }}
            </v-stepper-step>
            <v-stepper-step :step="2">
              {{ $t('dashboard.snapshot.edit.dialog.location_data.title') }}
            </v-stepper-step>
            <v-stepper-step :step="3">
              {{ $t('common.total') }}
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
                v-model="snapshotData.locationDataSnapshot"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="save"
              />
            </v-stepper-content>
            <v-stepper-content :step="3" class="pa-0">
              <edit-snapshot-total
                v-if="step === 3"
                v-model="snapshotData.locationDataSnapshot"
                :balances-snapshot="snapshotData.balancesSnapshot"
                :timestamp="timestamp"
                @update:step="step = $event"
                @input="finish"
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
          {{ $t('dashboard.snapshot.edit.dialog.fetch.loading') }}
        </div>
      </div>
    </v-card>
  </v-dialog>
</template>
<script lang="ts">
import { get, set } from '@vueuse/core';
import { defineComponent, onMounted, ref, toRefs } from 'vue';
import EditBalancesSnapshotTable from '@/components/dashboard/EditBalancesSnapshotTable.vue';
import EditLocationDataSnapshotTable from '@/components/dashboard/EditLocationDataSnapshotTable.vue';
import EditSnapshotTotal from '@/components/dashboard/EditSnapshotTotal.vue';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { Snapshot, SnapshotPayload } from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { useStatisticsStore } from '@/store/statistics';
import { showMessage } from '@/store/utils';
import { sortDesc } from '@/utils/bignumbers';

export default defineComponent({
  name: 'EditSnapshotDialog',
  components: {
    EditSnapshotTotal,
    EditLocationDataSnapshotTable,
    EditBalancesSnapshotTable
  },
  props: {
    timestamp: {
      required: true,
      type: Number
    }
  },
  emits: ['close', 'finish'],
  setup(props, { emit }) {
    const { timestamp } = toRefs(props);

    const snapshotData = ref<Snapshot | null>(null);
    const step = ref<number>(1);
    const { fetchNetValue } = useStatisticsStore();

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

    onMounted(() => {
      fetchSnapshotData();
    });

    const close = () => {
      emit('close');
    };

    const { notify } = useNotifications();
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
          title: i18n
            .t('dashboard.snapshot.edit.dialog.message.title')
            .toString(),
          message: i18n
            .t('dashboard.snapshot.edit.dialog.message.error', { message: e })
            .toString(),
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

    const finish = async () => {
      const success = await save();

      if (success) {
        showMessage(
          i18n.t('dashboard.snapshot.edit.dialog.message.success').toString(),
          i18n.t('dashboard.snapshot.edit.dialog.message.title').toString()
        );
        fetchNetValue();
        emit('finish');
      }
    };

    return {
      snapshotData,
      step,
      close,
      save,
      finish
    };
  }
});
</script>
<style module lang="scss">
.table {
  scroll-behavior: smooth;
  max-height: calc(100vh - 310px);
  overflow: auto;
}

.asset-select {
  max-width: 640px;
}

.raise {
  position: relative;
  z-index: 2;
}
</style>
