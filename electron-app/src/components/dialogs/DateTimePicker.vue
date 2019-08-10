<template>
  <v-menu
    ref="menu"
    v-model="menu"
    :close-on-content-click="false"
    transition="scale-transition"
    offset-y
    full-width
    max-width="580px"
    class="date-time-picker"
    :nudge-right="20"
  >
    <template #activator="{ on }">
      <v-text-field
        :value="value"
        :label="label"
        :hint="hint"
        :persistent-hint="persistentHint"
        :rules="rules"
        v-on="on"
      ></v-text-field>
    </template>

    <div class="menu-body">
      <v-date-picker v-model="dateModel" :max="maxDate"></v-date-picker>
      <v-time-picker v-model="timeModel" :max="maxTime"></v-time-picker>
    </div>
  </v-menu>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { VuetifyRuleValidations } from 'vuetify/src/mixins/validatable/index';

@Component({})
export default class DateTimePicker extends Vue {
  @Prop({ required: true })
  label!: string;
  @Prop({ required: false, default: '' })
  hint!: string;
  @Prop({ required: false, default: false, type: Boolean })
  persistentHint!: boolean;
  @Prop({ required: true })
  value!: string;
  @Prop({ default: () => [] })
  rules!: VuetifyRuleValidations;
  @Prop({ required: false, default: false, type: Boolean })
  limitNow!: boolean;

  timeModel: string = '00:00';
  dateModel: string = '';

  maxDate: string = '';
  maxTime: string = '';

  menu: boolean = false;

  private setMaxTime() {
    if (this.limitNow) {
      this.maxTime = new Date().toISOString().split('T')[1];
    }
  }

  private setMaxDate() {
    if (this.limitNow) {
      this.maxDate = new Date().toISOString().split('T')[0];
    }
  }

  private updateActualDate() {
    const value = `${this.formatDate(this.dateModel)} ${this.timeModel}`;
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
      this.timeModel = '00:00';
    }
  }

  @Emit()
  public input(value?: string) {}

  formatDate(date: string) {
    if (!date) return '';

    const [year, month, day] = date.split('-');
    return `${day}/${month}/${year}`;
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
