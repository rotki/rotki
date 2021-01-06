<template>
  <v-row>
    <v-col cols="12">
      <span class="title">{{ $t('generate.period') }}</span>
      <v-chip-group v-model="yearSelection" mandatory>
        <v-chip
          v-for="period in periods"
          :key="period"
          class="ma-2"
          :value="period"
          label
          small
        >
          {{ period }}
        </v-chip>
        <v-chip value="custom" class="ma-2" small label>
          {{ $t('generate.custom_selection') }}
        </v-chip>
      </v-chip-group>
    </v-col>
    <v-col v-if="yearSelection !== 'custom'" cols="12">
      <span class="title">{{ $t('generate.sub_period_label') }}</span>
      <v-chip-group v-model="detailsSelection" mandatory>
        <v-chip
          v-for="subPeriod in subPeriod"
          :key="subPeriod.id"
          :value="subPeriod.id"
          :disabled="isStartAfterNow(subPeriod.id)"
          label
          class="ma-2"
          small
        >
          {{ subPeriod.name }}
        </v-chip>
      </v-chip-group>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import moment from 'moment';
import { Component, Emit, Vue, Watch } from 'vue-property-decorator';

type ChangedParams = { start: string; end: string };

const Q1 = 'Q1';
const Q2 = 'Q2';
const Q3 = 'Q3';
const Q4 = 'Q4';
const ALL = 'ALL';

const QUARTERS = [Q1, Q2, Q3, Q4, ALL] as const;
type Quarter = typeof QUARTERS[number];

const QUARTER_STARTS: { [quarter in Quarter]: string } = {
  [ALL]: '01/01',
  [Q1]: '01/01',
  [Q2]: '01/04',
  [Q3]: '01/07',
  [Q4]: '01/10'
};

const QUARTER_ENDS: { [quarter in Quarter]: string } = {
  [Q1]: '31/03',
  [Q2]: '30/06',
  [Q3]: '30/09',
  [Q4]: '31/12',
  [ALL]: '31/12'
};

@Component({})
export default class ReportPeriodSelector extends Vue {
  yearSelection: string = new Date().getFullYear().toString();
  detailsSelection: Quarter = ALL;

  isStartAfterNow(selection: Quarter) {
    const start = this.startDateTime(selection);
    const startEpoch = moment(start, 'DD/MM/YYYY HH:mm:ss').unix();
    return startEpoch >= moment().unix();
  }

  startDateTime(selection: Quarter): string {
    const startDate = QUARTER_STARTS[selection];
    return `${startDate}/${this.yearSelection} 00:00`;
  }

  get start(): string {
    return this.startDateTime(this.detailsSelection);
  }

  get end(): string {
    const endDate = QUARTER_ENDS[this.detailsSelection];
    return `${endDate}/${this.yearSelection} 23:59:59`;
  }

  private get isCustom(): boolean {
    return this.yearSelection === 'custom';
  }

  @Watch('yearSelection')
  onSelectionChange() {
    this.custom(this.isCustom);
    if (!this.isCustom) {
      this.changed({ start: this.start, end: this.end });
    }
  }

  @Watch('detailsSelection')
  onDetailSelectionChange() {
    if (!this.isCustom) {
      this.changed({ start: this.start, end: this.end });
    }
  }

  created() {
    this.changed({ start: this.start, end: this.end });
  }

  @Emit()
  changed(_event: ChangedParams) {}

  @Emit()
  custom(_value: boolean) {}

  get periods(): string[] {
    const periods: string[] = [];
    const fullYear = new Date().getFullYear();
    for (let year = fullYear; year > fullYear - 5; year--) {
      periods.push(year.toString());
    }
    return periods;
  }

  get subPeriod() {
    return [
      {
        id: ALL,
        name: this.$t('generate.sub_period.all').toString()
      },
      {
        id: Q1,
        name: 'Q1'
      },
      {
        id: Q2,
        name: 'Q2'
      },
      {
        id: Q3,
        name: 'Q3'
      },
      {
        id: Q4,
        name: 'Q4'
      }
    ];
  }
}
</script>

<style scoped lang="scss"></style>
