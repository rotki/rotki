<template>
  <v-select
    v-bind="$attrs"
    item-text="text"
    item-value="value"
    outlined
    persistent-hint
    :items="selections"
    v-on="$listeners"
  >
    <template #item="{ item, attrs, on }">
      <v-list-item v-bind="attrs" v-on="on">
        <v-list-item-content>
          <v-list-item-title>
            {{ item.text }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ item.description }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
    </template>
    <template #append-outer>
      <slot />
    </template>
  </v-select>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class RoundingSelector extends Vue {
  readonly selections = [
    {
      value: BigNumber.ROUND_UP,
      text: this.$t('rounding_settings.round.up').toString(),
      description: this.$t('rounding_settings.round.up_description').toString()
    },
    {
      value: BigNumber.ROUND_DOWN,
      text: this.$t('rounding_settings.round.down').toString(),
      description: this.$t(
        'rounding_settings.round.down_description'
      ).toString()
    },
    {
      value: BigNumber.ROUND_HALF_EVEN,
      text: this.$t('rounding_settings.round.half_even').toString(),
      description: this.$t(
        'rounding_settings.round.half_even_description'
      ).toString()
    }
  ];
}
</script>
