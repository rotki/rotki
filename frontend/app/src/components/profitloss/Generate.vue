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
import { defineComponent, ref } from '@vue/composition-api';
import RangeSelector from '@/components/helper/date/RangeSelector.vue';
import { convertToTimestamp } from '@/utils/date';

export default defineComponent({
  name: 'Generate',
  components: {
    RangeSelector
  },
  emits: ['generate'],
  setup(_, { emit }) {
    const range = ref({ start: '', end: '' });
    const valid = ref(false);
    const generate = () => {
      const start = convertToTimestamp(range.value.start);
      const end = convertToTimestamp(range.value.end);
      emit('generate', {
        start,
        end
      });
    };
    return {
      range,
      valid,
      generate
    };
  }
});
</script>
