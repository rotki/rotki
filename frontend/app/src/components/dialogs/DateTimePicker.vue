<template>
  <div>
    <v-menu
      ref="menu"
      v-model="menu"
      :close-on-content-click="false"
      transition="scale-transition"
      offset-y
      max-width="600px"
      class="date-time-picker"
    >
      <template #activator="{ on }">
        <v-text-field
          ref="input"
          :value="inputtedDate"
          :label="label"
          :hint="hint"
          :disabled="disabled"
          prepend-inner-icon="mdi-calendar"
          :persistent-hint="persistentHint"
          :rules="allRules"
          :outlined="outlined"
          append-icon="mdi-clock-outline"
          :error-messages="errorMessages"
          @change="emitIfValid($event)"
          @click:append="setNow()"
          v-on="on"
        />
      </template>

      <div class="menu-body">
        <v-date-picker
          class="rounded-0"
          :value="dateModel"
          :max="maxDate"
          @change="onDateChange($event)"
        />
        <v-time-picker
          class="rounded-0"
          :value="timeModel"
          :max="maxTime"
          format="24hr"
          :use-seconds="seconds"
          @change="onTimeChange($event)"
        />
      </div>
      <div class="pa-4 pb-0">
        <v-autocomplete
          v-model="selectedTimezone"
          :items="timezones"
          outlined
          :rules="timezoneRule"
          persistent-hint
          menu-pros="auto"
        />
      </div>
    </v-menu>
  </div>
</template>

<script lang="ts">
import dayjs from 'dayjs';
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { timezones } from '@/data/timezones';
import { DateFormat } from '@/types/date-format';
import {
  changeDateFormat,
  convertDateByTimezone,
  getDateInputISOFormat,
  isValidDate
} from '@/utils/date';

@Component({
  computed: {
    ...mapGetters('settings', ['dateInputFormat'])
  }
})
export default class DateTimePicker extends Vue {
  private static dateFormat = 'YYYY-MM-DD';

  @Prop({ required: true })
  label!: string;
  @Prop({ required: false, default: '' })
  hint!: string;
  @Prop({ required: false, default: false, type: Boolean })
  persistentHint!: boolean;
  @Prop({ default: '' })
  value!: string;
  @Prop({ default: () => [] })
  rules!: ((v: string) => boolean | string)[];
  @Prop({ required: false, default: false, type: Boolean })
  limitNow!: boolean;
  @Prop({ required: false, default: false, type: Boolean })
  seconds!: boolean;
  @Prop({ required: false, default: false, type: Boolean })
  outlined!: boolean;
  @Prop({ required: false, default: false, type: Boolean })
  disabled!: boolean;
  @Prop({ required: false, default: () => [], type: Array })
  errorMessages!: string[];

  dateInputFormat!: DateFormat;
  inputtedDate: string = '';
  selectedTimezone: string = '';

  get timezones(): string[] {
    return timezones;
  }

  readonly timezoneRule = [
    (v: string) => !!v || this.$t('date_time_picker.timezone_field.non_empty')
  ];

  private dateFormatRule(date: string) {
    let dateFormat: string = getDateInputISOFormat(this.dateInputFormat);

    if (this.seconds) {
      return (
        this.isValid(date) ||
        this.$t('date_time_picker.seconds_format', {
          dateFormat
        }).toString()
      );
    }
    return (
      this.isValid(date) ||
      this.$t('date_time_picker.default_format', {
        dateFormat
      }).toString()
    );
  }

  timeModel: string = dayjs().format(this.timeFormat);
  dateModel: string = '';

  get maxDate(): string {
    if (this.limitNow) {
      return dayjs().format(DateTimePicker.dateFormat);
    }
    return '';
  }

  get maxTime(): string {
    if (this.limitNow && dayjs(this.dateModel).isToday()) {
      return dayjs().format(this.timeFormat);
    }
    return '';
  }

  menu: boolean = false;

  private get timeFormat(): string {
    let format = 'HH:mm';
    if (this.seconds) {
      format += ':ss';
    }
    return format;
  }

  get allRules(): ((v: string) => boolean | string)[] {
    return this.rules.concat([this.dateFormatRule.bind(this)]);
  }

  private updateActualDate() {
    let value = this.formatDate(this.dateModel);
    if (this.timeModel) {
      value += ` ${this.timeModel}`;
    }

    this.emitIfValid(value, DateFormat.DateMonthYearHourMinuteSecond);
  }

  private emitIfValid(
    value: string,
    format: DateFormat = this.dateInputFormat
  ) {
    if (this.isValid(value, format)) {
      const formattedDate = changeDateFormat(
        value,
        format,
        DateFormat.DateMonthYearHourMinuteSecond
      );
      this.input(
        convertDateByTimezone(
          formattedDate,
          DateFormat.DateMonthYearHourMinuteSecond,
          this.selectedTimezone,
          dayjs.tz.guess()
        )
      );
    }
  }

  private isValid(
    date: string,
    format: DateFormat = this.dateInputFormat
  ): boolean {
    let dateFormat = getDateInputISOFormat(format);

    if (this.seconds) {
      return (
        isValidDate(date, dateFormat) ||
        isValidDate(date, dateFormat + ' HH:mm:ss')
      );
    }
    return (
      isValidDate(date, dateFormat) || isValidDate(date, dateFormat + ' HH:mm')
    );
  }

  created() {
    this.setCurrentTimezone();
  }

  mounted() {
    this.onValueChange(this.value);
  }

  getDefaultTimezoneName(offset: number) {
    let hour = offset / 60;
    if (!Number.isInteger(offset)) hour = 0;

    const isPositive = hour > 0;
    return `Etc/GMT${isPositive ? '+' : ''}hour`;
  }

  setCurrentTimezone() {
    const guessedTimezone = dayjs.tz.guess();
    const offset = dayjs().utcOffset() / 60;

    // check if guessed timezones exist in our timezones list
    const isTimezoneExist = this.timezones.filter(
      timezone => timezone === guessedTimezone
    );

    this.selectedTimezone = isTimezoneExist
      ? guessedTimezone
      : this.getDefaultTimezoneName(offset);
  }

  @Watch('selectedTimezone')
  onTimezoneChange() {
    this.onValueChange(this.value);
  }

  onTimeChange(time: string) {
    this.timeModel = time;
    this.updateActualDate();
  }

  onDateChange(date: string) {
    this.dateModel = date;
    this.updateActualDate();
  }

  @Watch('value')
  onValueChange(value: string) {
    const changedDateTimezone = convertDateByTimezone(
      value,
      DateFormat.DateMonthYearHourMinuteSecond,
      dayjs.tz.guess(),
      this.selectedTimezone
    );
    this.inputtedDate = changeDateFormat(
      changedDateTimezone,
      DateFormat.DateMonthYearHourMinuteSecond,
      this.dateInputFormat
    );

    if (!value) {
      this.dateModel = '';
      this.timeModel = '';
    } else if (this.isValid(value, DateFormat.DateMonthYearHourMinuteSecond)) {
      const [date, time] = changedDateTimezone.split(' ');
      const [day, month, year] = date.split('/');
      const formattedDate = `${year}-${month}-${day}`;
      if (formattedDate !== this.dateModel) {
        this.dateModel = formattedDate;
      }
      if (time !== this.timeModel) {
        this.timeModel = time;
      }
    }
  }

  @Emit()
  public input(_value?: string) {}

  formatDate(date: string) {
    if (!date) return '';

    const [year, month, day] = date.split('-');
    return `${day}/${month}/${year}`;
  }

  setNow() {
    const now = dayjs();
    this.timeModel = now.format(this.timeFormat);
    this.dateModel = now.format(DateTimePicker.dateFormat);
    this.updateActualDate();
  }

  reset() {
    (this.$refs.input as any).reset();
  }
}
</script>

<style scoped lang="scss">
.menu-body {
  z-index: 999;
  display: flex;
  flex-direction: row;

  ::v-deep {
    .v-picker {
      &__title {
        height: 102px;
      }
    }

    .v-card {
      box-shadow: none !important;
    }
  }

  &:first-child {
    ::v-deep {
      .v-picker {
        border-top-right-radius: 0 !important;
        border-bottom-right-radius: 0 !important;
      }
    }
  }

  &:last-child {
    ::v-deep {
      .v-picker {
        border-top-left-radius: 0 !important;
        border-bottom-left-radius: 0 !important;
      }
    }
  }
}
</style>
