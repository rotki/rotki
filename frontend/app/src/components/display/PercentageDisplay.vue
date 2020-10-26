<template>
  <v-row
    no-gutters
    class="percentage-display"
    :justify="justify"
    align="center"
  >
    <v-col
      :cols="justify === 'end' ? null : 'auto'"
      :style="privacyStyle"
      :class="justify === 'end' ? 'text-end' : 'text-start'"
    >
      {{ displayValue }}
    </v-col>
    <v-col
      v-if="!!value"
      :style="assetStyle"
      :class="assetPadding ? 'mr-1' : null"
      class="ml-1 percentage-display__symbol text--secondary"
      :cols="justify === 'start' ? null : 'auto'"
    >
      {{ $t('percentage_display.symbol') }}
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Mixins } from 'vue-property-decorator';
import PrivacyMixin from '@/mixins/privacy-mixin';
import ScrambleMixin from '@/mixins/scramble-mixin';

@Component({})
export default class PercentageDisplay extends Mixins(
  ScrambleMixin,
  PrivacyMixin
) {
  @Prop({
    required: true,
    validator: (value: any) => typeof value === 'string' || value === null
  })
  value!: string | null;
  @Prop({
    required: false,
    type: String,
    default: 'end',
    validator: (value: any) => {
      return ['end', 'start'].includes(value);
    }
  })
  justify!: 'end' | 'start';
  @Prop({
    required: false,
    type: Number,
    default: 0,
    validator: chars => chars >= 0 && chars <= 5
  })
  assetPadding!: number;

  get displayValue(): string {
    if (this.scrambleData) {
      return (Math.random() * 100 + 1).toFixed(2);
    }
    if (!this.value) {
      return '-';
    }
    return this.value.replace('%', '');
  }

  get assetStyle(): { [key: string]: string } {
    if (!this.assetPadding) {
      return {
        'max-width': '0ch'
      };
    }
    return {
      width: `${this.assetPadding + 1}ch`,
      'text-align': 'start'
    };
  }
}
</script>

<style scoped lang="scss">
.percentage-display {
  &__symbol {
    font-size: 0.8em;
  }
}
</style>
