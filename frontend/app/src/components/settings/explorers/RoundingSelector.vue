<template>
  <v-select
    v-bind="rootAttrs"
    item-text="text"
    item-value="value"
    outlined
    persistent-hint
    :items="selections"
    v-on="rootListeners"
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

<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { useListeners } from 'vue';

const rootAttrs = useAttrs();
const rootListeners = useListeners();
const { t } = useI18n();

const selections = [
  {
    value: BigNumber.ROUND_UP,
    text: t('rounding_settings.round.up').toString(),
    description: t('rounding_settings.round.up_description').toString()
  },
  {
    value: BigNumber.ROUND_DOWN,
    text: t('rounding_settings.round.down').toString(),
    description: t('rounding_settings.round.down_description').toString()
  },
  {
    value: BigNumber.ROUND_HALF_EVEN,
    text: t('rounding_settings.round.half_even').toString(),
    description: t('rounding_settings.round.half_even_description').toString()
  }
];
</script>
