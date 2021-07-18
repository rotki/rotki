<template>
  <v-row>
    <v-col cols="12">
      <span class="text-h6">{{ $t('generate.period') }}</span>
      <v-chip-group
        :value="year"
        mandatory
        @change="onChange({ year: $event })"
      >
        <v-chip
          v-for="period in periods"
          :key="period"
          :color="year === period ? 'primary' : null"
          class="ma-2"
          :value="period"
          label
          small
        >
          {{ period }}
        </v-chip>
        <v-chip
          value="custom"
          class="ma-2"
          small
          label
          :color="isCustom ? 'primary' : null"
        >
          {{ $t('generate.custom_selection') }}
        </v-chip>
      </v-chip-group>
    </v-col>
    <v-col v-if="year !== 'custom'" cols="12">
      <span class="text-h6">{{ $t('generate.sub_period_label') }}</span>
      <v-chip-group
        :value="quarter"
        mandatory
        @change="onChange({ quarter: $event })"
      >
        <v-chip
          v-for="subPeriod in subPeriod"
          :key="subPeriod.id"
          :color="quarter === subPeriod.id ? 'primary' : null"
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
import dayjs from 'dayjs';
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { ALL, Q1, Q2, Q3, Q4, QUARTERS } from '@/store/settings/consts';
import { Quarter } from '@/store/settings/types';

export type PeriodChangedEvent = {
  start: string;
  end: string;
};

export type SelectionChangedEvent = {
  readonly year: string | 'custom';
  readonly quarter: Quarter;
};

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
  @Prop({
    required: true,
    type: String,
    default: () => new Date().getFullYear().toString()
  })
  year!: string | 'custom';
  @Prop({
    required: true,
    type: String,
    default: ALL,
    validator: value => QUARTERS.includes(value)
  })
  quarter!: Quarter;

  isStartAfterNow(selection: Quarter) {
    const start = this.startDateTime(selection);
    return dayjs(start, 'DD/MM/YYYY HH:mm').isAfter(dayjs());
  }

  startDateTime(selection: Quarter): string {
    const startDate = QUARTER_STARTS[selection];
    return `${startDate}/${this.year} 00:00`;
  }

  onChange(change: { year?: string; quarter?: Quarter }) {
    const year = change?.year ?? this.year;
    const quarter = change?.quarter ?? this.quarter;

    this.changed({ year, quarter });
    this.periodUpdate(year !== 'custom' ? this.periodEventPayload : null);
  }

  get start(): string {
    return this.startDateTime(this.quarter);
  }

  mounted() {
    this.periodUpdate(this.year !== 'custom' ? this.periodEventPayload : null);
  }

  get end(): string {
    const endDate = QUARTER_ENDS[this.quarter];
    return `${endDate}/${this.year} 23:59:59`;
  }

  get periodEventPayload(): PeriodChangedEvent {
    return {
      start: this.start,
      end: this.end
    };
  }

  private get isCustom(): boolean {
    return this.year === 'custom';
  }

  @Watch('quarter')
  onQuarterChange() {
    this.periodUpdate(this.isCustom ? null : this.periodEventPayload);
  }

  @Watch('year')
  onYearChange() {
    this.periodUpdate(this.isCustom ? null : this.periodEventPayload);
  }

  @Emit()
  periodUpdate(_event: PeriodChangedEvent | null) {}

  @Emit()
  changed(_value: SelectionChangedEvent) {}

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
