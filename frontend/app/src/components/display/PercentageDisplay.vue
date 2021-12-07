<template>
  <v-row
    no-gutters
    class="percentage-display flex-nowrap"
    :justify="justify"
    align="center"
  >
    <v-col
      :cols="justify === 'end' ? null : 'auto'"
      class="percentage-display__amount"
      :class="{
        'blur-content': !shouldShowPercentage,
        'text-end': justify === 'end',
        'text-start': justify !== 'start'
      }"
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
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import ScrambleMixin from '@/mixins/scramble-mixin';

@Component({
  computed: {
    ...mapGetters('session', ['shouldShowPercentage'])
  }
})
export default class PercentageDisplay extends Mixins(ScrambleMixin) {
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
  shouldShowPercentage!: boolean;

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
  &__amount {
    &.blur-content {
      filter: blur(0.75em);
    }
  }

  &__symbol {
    font-size: 0.8em;
  }
}
</style>
