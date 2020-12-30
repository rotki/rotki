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
import { Component, Emit, Vue, Watch } from 'vue-property-decorator';

type ChangedParams = { start: string; end: string };

@Component({})
export default class ReportPeriodSelector extends Vue {
  yearSelection: string = new Date().getFullYear().toString();
  detailsSelection: string = 'ALL';

  get start(): string {
    let startDate: string;
    if (this.detailsSelection === 'Q2') {
      startDate = '01/04';
    } else if (this.detailsSelection === 'Q3') {
      startDate = '01/07';
    } else if (this.detailsSelection === 'Q4') {
      startDate = '01/10';
    } else {
      startDate = '01/01';
    }

    return `${startDate}/${this.yearSelection} 00:00`;
  }

  get end(): string {
    let endDate: string;
    if (this.detailsSelection === 'Q1') {
      endDate = '31/03';
    } else if (this.detailsSelection === 'Q2') {
      endDate = '30/06';
    } else if (this.detailsSelection === 'Q3') {
      endDate = '30/09';
    } else {
      endDate = '31/12';
    }
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
        id: 'ALL',
        name: this.$t('generate.sub_period.all').toString()
      },
      {
        id: 'Q1',
        name: 'Q1'
      },
      {
        id: 'Q2',
        name: 'Q2'
      },
      {
        id: 'Q3',
        name: 'Q3'
      },
      {
        id: 'Q4',
        name: 'Q4'
      }
    ];
  }
}
</script>

<style scoped lang="scss"></style>
