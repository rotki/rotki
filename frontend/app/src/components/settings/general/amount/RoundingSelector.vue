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

<template>
  <VSelect
    v-bind="rootAttrs"
    item-text="text"
    item-value="value"
    outlined
    persistent-hint
    :items="selections"
    v-on="rootListeners"
  >
    <template #item="{ item, attrs, on }">
      <ListItem
        no-hover
        no-padding
        v-bind="attrs"
        :title="item.text"
        :subtitle="item.description"
        v-on="on"
      />
    </template>
    <template #append-outer>
      <slot />
    </template>
  </VSelect>
</template>
