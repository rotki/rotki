<template>
  <v-form v-model="valid">
    <v-card>
      <v-card-title>
        <card-title>{{ $t('generate.title') }}</card-title>
      </v-card-title>
      <v-card-text>
        <range-selector v-model="range" />
      </v-card-text>
      <v-card-actions>
        <v-btn
          color="primary"
          depressed
          :disabled="!valid"
          @click="generate()"
          v-text="$t('generate.generate')"
        />
      </v-card-actions>
    </v-card>
  </v-form>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import RangeSelector, {
  SelectedRange
} from '@/components/helper/date/RangeSelector.vue';
import ReportPeriodSelector from '@/components/profitloss/ReportPeriodSelector.vue';
import { convertToTimestamp } from '@/utils/date';

@Component({
  components: {
    RangeSelector,
    ReportPeriodSelector,
    DateTimePicker
  },
  methods: {}
})
export default class Generate extends Vue {
  range: SelectedRange = { start: '', end: '' };
  valid: boolean = false;

  generate() {
    const start = convertToTimestamp(this.range.start);
    const end = convertToTimestamp(this.range.end);
    this.$emit('generate', {
      start,
      end
    });
  }
}
</script>

<style scoped></style>
