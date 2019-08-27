<template>
  <v-form v-model="valid">
    <v-card>
      <v-card-title>Generate</v-card-title>
      <v-card-text>
        <v-layout>
          <v-flex xs12>
            <date-time-picker
              v-model="start"
              label="Start Date"
              limit-now
              :rules="startRules"
            ></date-time-picker>
          </v-flex>
        </v-layout>
        <v-layout>
          <v-flex xs12>
            <date-time-picker
              v-model="end"
              label="End Date"
              limit-now
              :rules="endRules"
            ></date-time-picker>
          </v-flex>
        </v-layout>
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
        >
          Generate
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-form>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import { VuetifyRuleValidations } from 'vuetify/src/mixins/validatable/index';
import { convertToTimestamp } from '@/utils/conversion';

@Component({
  components: {
    DateTimePicker
  }
})
export default class Generate extends Vue {
  start: string = '';
  end: string = '';
  valid: boolean = false;
  invalidRange: boolean = false;
  message: string = '';

  date = /^([0-2]\d|[3][0-1])\/([0]\d|[1][0-2])\/([2][01]|[1][6-9])\d{2}(\s([0-1]\d|[2][0-3])(:[0-5]\d))?$/;

  startRules: VuetifyRuleValidations = [
    (v: string) => !!v || 'Start date cannot be empty',
    (v: string) =>
      (v && this.date.test(v)) || 'Date should be in DD/MM/YYYY HH:MM format'
  ];

  endRules: VuetifyRuleValidations = [
    (v: string) => !!v || 'End date cannot be empty',
    (v: string) =>
      (v && this.date.test(v)) || 'Date should be in DD/MM/YYYY HH:MM format'
  ];

  @Watch('start')
  onStartChange() {
    this.invalidRange =
      convertToTimestamp(this.start) > convertToTimestamp(this.end);
    this.message = 'The end time should be after the start time.';
  }

  @Watch('end')
  onEndChange() {
    this.invalidRange =
      convertToTimestamp(this.start) > convertToTimestamp(this.end);
    this.message = 'The end time should be after the start time.';
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
