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
} from '@/components/taxreport/ReportPeriodSelector.vue';
import { ALL, TAX_REPORT_PERIOD } from '@/store/settings/consts';
import {
  FrontendSettingsPayload,
  Quarter,
  TaxReportPeriod
} from '@/store/settings/types';
import { ActionStatus } from '@/store/types';

@Component({
  components: {
    ReportPeriodSelector,
    DateTimePicker
  },
  computed: {
    ...mapGetters('settings', [TAX_REPORT_PERIOD])
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

  [TAX_REPORT_PERIOD]!: TaxReportPeriod;
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
    this.year = this.taxReportPeriod.year;
    this.quarter = this.taxReportPeriod.quarter;
  }

  private convertToTimestamp(date: string): number {
    let format: string = 'DD/MM/YYYY';
    if (date.indexOf(' ') > -1) {
      format += ' HH:mm';
      if (date.charAt(date.length - 6) === ':') {
        format += ':ss';
      }
    }

    return moment(date, format).unix();
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
    if (this.convertToTimestamp(period.end) > moment().unix()) {
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
      taxReportPeriod: event
    });
  }

  @Watch('start')
  onStartChange() {
    this.invalidRange =
      !!this.start &&
      !!this.end &&
      this.convertToTimestamp(this.start) > this.convertToTimestamp(this.end);
    this.message = this.$t('generate.validation.end_after_start').toString();
  }

  @Watch('end')
  onEndChange() {
    this.invalidRange =
      !!this.start &&
      !!this.end &&
      this.convertToTimestamp(this.start) > this.convertToTimestamp(this.end);
    this.message = this.$t('generate.validation.end_after_start').toString();
  }

  generate() {
    const start = this.convertToTimestamp(this.start);
    const end = this.convertToTimestamp(this.end);
    this.$emit('generate', {
      start,
      end
    });
  }
}
</script>

<style scoped></style>
