<template>
  <v-form v-model="valid">
    <v-card>
      <v-card-title v-text="$t('generate.title')" />
      <v-card-text>
        <report-period-selector
          :year="year"
          :quarter="quarter"
          @period-update="onPeriodChange"
          @changed="onChanged"
        />
        <v-row v-if="custom">
          <v-col cols="12">
            <date-time-picker
              v-model="start"
              label="Start Date"
              limit-now
              :rules="startRules"
            />
          </v-col>
          <v-col cols="12">
            <date-time-picker
              v-model="end"
              label="End Date"
              limit-now
              :rules="endRules"
            />
          </v-col>
        </v-row>
        <v-alert v-model="invalidRange" type="error">
          {{ message }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-btn
          color="primary"
          depressed
          :disabled="!valid || invalidRange"
          @click="generate()"
          v-text="$t('generate.generate')"
        />
      </v-card-actions>
    </v-card>
  </v-form>
</template>

<script lang="ts">
import moment from 'moment';
import { Component, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import ReportPeriodSelector, {
  PeriodChangedEvent,
  SelectionChangedEvent
} from '@/components/profitloss/ReportPeriodSelector.vue';
import { ALL, PROFIT_LOSS_PERIOD } from '@/store/settings/consts';
import {
  FrontendSettingsPayload,
  ProfitLossTimeframe,
  Quarter
} from '@/store/settings/types';
import { ActionStatus } from '@/store/types';
import { convertToTimestamp } from '@/utils/date';

@Component({
  components: {
    ReportPeriodSelector,
    DateTimePicker
  },
  computed: {
    ...mapGetters('settings', [PROFIT_LOSS_PERIOD])
  },
  methods: {
    ...mapActions('settings', ['updateSetting'])
  }
})
export default class Generate extends Vue {
  start: string = '';
  end: string = '';
  valid: boolean = false;
  invalidRange: boolean = false;
  message: string = '';
  year: string = new Date().getFullYear().toString();
  quarter: Quarter = ALL;

  [PROFIT_LOSS_PERIOD]!: ProfitLossTimeframe;
  updateSetting!: (payload: FrontendSettingsPayload) => Promise<ActionStatus>;

  startRules: ((v: string) => boolean | string)[] = [
    (v: string) =>
      !!v || this.$t('generate.validation.empty_start_date').toString()
  ];

  endRules: ((v: string) => boolean | string)[] = [
    (v: string) =>
      !!v || this.$t('generate.validation.empty_end_date').toString()
  ];

  mounted() {
    this.year = this[PROFIT_LOSS_PERIOD].year;
    this.quarter = this[PROFIT_LOSS_PERIOD].quarter;
  }

  get custom(): boolean {
    return this.year === 'custom';
  }

  onPeriodChange(period: PeriodChangedEvent | null) {
    if (period === null) {
      this.start = '';
      this.end = '';
      return;
    }

    this.start = period.start;
    if (convertToTimestamp(period.end) > moment().unix()) {
      this.end = moment().format('DD/MM/YYYY HH:mm:ss');
    } else {
      this.end = period.end;
    }
  }

  onChanged(event: SelectionChangedEvent) {
    this.year = event.year;
    this.quarter = event.quarter;

    if (event.year === 'custom') {
      this.start = '';
      this.end = '';
    }

    this.updateSetting({
      profitLossReportPeriod: event
    });
  }

  @Watch('start')
  onStartChange() {
    this.invalidRange =
      !!this.start &&
      !!this.end &&
      convertToTimestamp(this.start) > convertToTimestamp(this.end);
    this.message = this.$t('generate.validation.end_after_start').toString();
  }

  @Watch('end')
  onEndChange() {
    this.invalidRange =
      !!this.start &&
      !!this.end &&
      convertToTimestamp(this.start) > convertToTimestamp(this.end);
    this.message = this.$t('generate.validation.end_after_start').toString();
  }

  generate() {
    const start = convertToTimestamp(this.start);
    const end = convertToTimestamp(this.end);
    this.$emit('generate', {
      start,
      end
    });
  }
}
</script>

<style scoped></style>
