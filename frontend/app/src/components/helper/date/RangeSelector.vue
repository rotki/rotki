<template>
  <div class="range-selector">
    <report-period-selector
      :year="year"
      :quarter="quarter"
      @period-update="onPeriodChange"
      @changed="onChanged"
    />
    <v-row v-if="custom">
      <v-col cols="12" md="6">
        <date-time-picker
          :value="value.start"
          outlined
          label="Start Date"
          limit-now
          :rules="startRules"
          @input="$emit('input', { start: $event, end: value.end })"
        />
      </v-col>
      <v-col cols="12" md="6">
        <date-time-picker
          :value="value.end"
          outlined
          label="End Date"
          limit-now
          :rules="endRules"
          @input="$emit('input', { start: value.start, end: $event })"
        />
      </v-col>
    </v-row>
    <v-alert v-model="invalidRange" type="error" dense>
      {{ $t('generate.validation.end_after_start') }}
    </v-alert>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, inject } from '@vue/composition-api';
import dayjs from 'dayjs';
import { Store } from 'vuex';
import ReportPeriodSelector, {
  PeriodChangedEvent,
  SelectionChangedEvent
} from '@/components/profitloss/ReportPeriodSelector.vue';
import { RotkehlchenState } from '@/store/types';
import { assert } from '@/utils/assertions';
import { convertToTimestamp } from '@/utils/date';

export interface SelectedRange {
  readonly start: string;
  readonly end: string;
}

export default defineComponent({
  name: 'RangeSelector',
  components: { ReportPeriodSelector },
  props: {
    value: {
      type: Object,
      required: true
    }
  },
  setup(_props, { emit }) {
    const store = inject<Store<RotkehlchenState>>('vuex-store');
    assert(store);
    const custom = computed(({ year }) => year === 'custom');
    const invalidRange = computed(
      ({ value }) =>
        !!value &&
        !!value.start &&
        !!value.end &&
        convertToTimestamp(value.start) > convertToTimestamp(value.end)
    );

    const year = computed(
      () => store.state.settings?.profitLossReportPeriod.year
    );
    const quarter = computed(
      () => store.state.settings?.profitLossReportPeriod.quarter
    );

    return {
      custom,
      year,
      quarter,
      invalidRange,
      onChanged: function (event: SelectionChangedEvent) {
        if (event.year === 'custom') {
          emit('input', { start: '', end: '' });
        }

        store.dispatch('settings/updateSetting', {
          profitLossReportPeriod: event
        });
      },
      onPeriodChange: function (period: PeriodChangedEvent | null) {
        if (period === null) {
          emit('input', { start: '', end: '' });
          return;
        }

        const start = period.start;
        let end = period.end;
        if (convertToTimestamp(period.end) > dayjs().unix()) {
          end = dayjs().format('DD/MM/YYYY HH:mm:ss');
        }
        emit('input', { start, end });
      }
    };
  },
  data: function () {
    return {
      startRules: [
        (v: string) =>
          !!v || this.$t('generate.validation.empty_start_date').toString()
      ],
      endRules: [
        (v: string) =>
          !!v || this.$t('generate.validation.empty_end_date').toString()
      ]
    };
  }
});
</script>

<style scoped lang="scss">
.range-selector {
  height: 260px;
}
</style>
