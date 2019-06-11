<template>
  <v-menu
    ref="menu"
    v-model="menu"
    :close-on-content-click="false"
    lazy
    transition="scale-transition"
    offset-y
    full-width
    max-width="580px"
    :nudge-right="20"
  >
    <template v-slot:activator="{ on }">
      <v-text-field
        :value="value"
        :label="label"
        :hint="hint"
        :persistent-hint="persistentHint"
        v-on="on"
      ></v-text-field>
    </template>

    <div class="menu-body">
      <v-date-picker v-model="dateModel"></v-date-picker>
      <v-time-picker v-model="timeModel"></v-time-picker>
    </div>
  </v-menu>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';

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

  timeModel: string = '00:00';
  dateModel: string = '';

  menu: boolean = false;

  private updateActualDate() {
    const value = `${this.formatDate(this.dateModel)} ${this.timeModel}`;
    this.input(value);
  }

  @Watch('timeModel')
  onTimeChange() {
    this.updateActualDate();
  }

  @Watch('dateModel')
  onDateChange() {
    this.updateActualDate();
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
  /deep/ .v-picker .v-picker__title {
    height: 102px;
  }

  /deep/ .v-card {
    box-shadow: none;
  }
}
</style>
