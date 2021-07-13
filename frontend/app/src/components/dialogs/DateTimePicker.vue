<template>
  <div>
    <v-menu
      ref="menu"
      v-model="menu"
      :close-on-content-click="false"
      transition="scale-transition"
      offset-y
      max-width="580px"
      class="date-time-picker"
    >
      <template #activator="{ on }">
        <v-text-field
          ref="input"
          :value="value"
          :label="label"
          :hint="hint"
          :disabled="disabled"
          prepend-inner-icon="mdi-calendar"
          :persistent-hint="persistentHint"
          :rules="allRules"
          :outlined="outlined"
          append-icon="mdi-clock-outline"
          @change="emitIfValid($event)"
          @click:append="setNow()"
          v-on="on"
        />
      </template>

      <div class="menu-body">
        <v-date-picker
          :value="dateModel"
          :max="maxDate"
          @change="onDateChange($event)"
        />
        <v-time-picker
          :value="timeModel"
          :max="maxTime"
          format="24hr"
          :use-seconds="seconds"
          @change="onTimeChange($event)"
        />
      </div>
    </v-menu>
  </div>
</template>

<script lang="ts">
import dayjs from 'dayjs';
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';

@Component({})
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

  private date = /^([0-2]\d|[3][0-1])\/([0]\d|[1][0-2])\/([2][01]|[1][6-9])\d{2}(\s([0-1]\d|[2][0-3])(:[0-5]\d))?$/;
  private withSeconds = /^([0-2]\d|[3][0-1])\/([0]\d|[1][0-2])\/([2][01]|[1][6-9])\d{2}(\s([0-1]\d|[2][0-3])(:[0-5]\d)(:[0-5]\d))$/;

  private dateFormatRule(v: string) {
    if (this.seconds) {
      return (
        (v && this.withSeconds.test(v)) ||
        this.$t('date_time_picker.seconds_format').toString()
      );
    }
    return (
      (v && this.date.test(v)) ||
      this.$t('date_time_picker.default_format').toString()
    );
  }

  timeModel: string = dayjs().format(this.timeFormat);
  dateModel: string = '';

  maxDate: string = '';
  maxTime: string = '';

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

  private setMaxTime() {
    if (this.limitNow) {
      this.maxTime = dayjs().format(this.timeFormat);
    }
  }

  private setMaxDate() {
    if (this.limitNow) {
      this.maxDate = dayjs().format(DateTimePicker.dateFormat);
    }
  }

  private updateActualDate() {
    let value = this.formatDate(this.dateModel);
    if (this.timeModel) {
      value += ` ${this.timeModel}`;
    }
    this.emitIfValid(value);
  }

  private emitIfValid(value: string) {
    if (this.isValid(value)) {
      this.input(value);
    }
  }

  private isValid(date: string): boolean {
    return this.seconds ? this.withSeconds.test(date) : this.date.test(date);
  }

  created() {
    this.setMaxDate();
    this.setMaxTime();
  }

  mounted() {
    this.onValueChange(this.value);
  }

  onTimeChange(time: string) {
    this.timeModel = time;
    this.updateActualDate();
    this.setMaxTime();
  }

  onDateChange(date: string) {
    this.dateModel = date;
    this.updateActualDate();
    this.setMaxDate();
  }

  @Watch('value')
  onValueChange(value?: string) {
    if (!value) {
      this.dateModel = '';
      this.timeModel = '';
    } else if (this.isValid(value)) {
      const [date, time] = value.split(' ');
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
