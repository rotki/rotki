<template>
  <v-form v-model="valid">
    <card>
      <template #title>
        {{ $t('generate.title') }}
      </template>
      <template #details>
        <v-tooltip top>
          <template #activator="{ on, attrs }">
            <v-btn
              text
              fab
              depressed
              v-bind="attrs"
              to="/settings/accounting"
              v-on="on"
            >
              <v-icon color="primary">mdi-cog</v-icon>
            </v-btn>
          </template>
          <span>{{ $t('profit_loss_report.settings_tooltip') }}</span>
        </v-tooltip>
      </template>
      <range-selector v-model="range" />
      <template #buttons>
        <v-btn
          color="primary"
          depressed
          :disabled="!valid"
          @click="generate()"
          v-text="$t('generate.generate')"
        />
      </template>
    </card>
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
