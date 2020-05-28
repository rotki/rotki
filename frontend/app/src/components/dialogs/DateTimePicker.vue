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
          :value="value"
          :label="label"
          :hint="hint"
          :persistent-hint="persistentHint"
          :rules="allRules"
          append-icon="fa-clock-o"
          @input="input($event)"
          @click:append="setNow()"
          v-on="on"
        ></v-text-field>
      </template>

      <div class="menu-body">
        <v-date-picker v-model="dateModel" :max="maxDate"></v-date-picker>
        <v-time-picker v-model="timeModel" :max="maxTime"></v-time-picker>
      </div>
    </v-menu>
  </div>
</template>

<script lang="ts">
import moment from 'moment';
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';

@Component({})
export default class DateTimePicker extends Vue {
  private static dateFormat = 'YYYY-MM-DD';
  private static timeFormat = 'HH:mm';

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

  private date = /^([0-2]\d|[3][0-1])\/([0]\d|[1][0-2])\/([2][01]|[1][6-9])\d{2}(\s([0-1]\d|[2][0-3])(:[0-5]\d))?$/;
  private dateFormatRule = (v: string) =>
    (v && this.date.test(v)) ||
    'Date should be in DD/MM/YYYY or DD/MM/YYYY HH:MM format';

  timeModel: string = moment().format(DateTimePicker.timeFormat);
  dateModel: string = '';

  maxDate: string = '';
  maxTime: string = '';

  menu: boolean = false;

  get allRules(): ((v: string) => boolean | string)[] {
    return this.rules.concat([this.dateFormatRule]);
  }

  private setMaxTime() {
    if (this.limitNow) {
      this.maxTime = moment().format(DateTimePicker.timeFormat);
    }
  }

  private setMaxDate() {
    if (this.limitNow) {
      this.maxDate = moment().format(DateTimePicker.dateFormat);
    }
  }

  private updateActualDate() {
    let value = this.formatDate(this.dateModel);
    if (this.timeModel) {
      value += ` ${this.timeModel}`;
    }
    this.input(value);
  }

  created() {
    this.setMaxDate();
    this.setMaxTime();
  }

  @Watch('timeModel')
  onTimeChange() {
    this.updateActualDate();
    this.setMaxTime();
  }

  @Watch('dateModel')
  onDateChange() {
    this.updateActualDate();
    this.setMaxDate();
  }

  @Watch('value')
  onValueChange() {
    if (!this.value) {
      this.dateModel = '';
      this.timeModel = '';
    } else if (this.date.test(this.value)) {
      const [date, time] = this.value.split(' ');
      const [day, month, year] = date.split('/');
      const formattedDate = `${year}-${month}-${day}`;
      if (formattedDate !== this.dateModel) {
        this.dateModel = formattedDate;
      }
      if (time != this.timeModel) {
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
    const now = moment();
    this.timeModel = now.format(DateTimePicker.timeFormat);
    this.dateModel = now.format(DateTimePicker.dateFormat);
  }
}
</script>

<style scoped lang="scss">
.menu-body {
  z-index: 999;
  display: flex;
  flex-direction: row;

  //noinspection CssInvalidPseudoSelector
  ::v-deep .v-picker .v-picker__title {
    height: 102px;
  }

  //noinspection CssInvalidPseudoSelector
  ::v-deep .v-card {
    box-shadow: none;
  }
}
</style>
