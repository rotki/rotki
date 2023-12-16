<script setup lang="ts">
import { BigNumber } from '@rotki/common';

const rootAttrs = useAttrs();
const { t } = useI18n();

const selections = [
  {
    value: BigNumber.ROUND_UP,
    text: t('rounding_settings.round.up').toString(),
    description: t('rounding_settings.round.up_description').toString(),
  },
  {
    value: BigNumber.ROUND_DOWN,
    text: t('rounding_settings.round.down').toString(),
    description: t('rounding_settings.round.down_description').toString(),
  },
  {
    value: BigNumber.ROUND_HALF_EVEN,
    text: t('rounding_settings.round.half_even').toString(),
    description: t('rounding_settings.round.half_even_description').toString(),
  },
];
</script>

<template>
  <VSelect
    v-bind="rootAttrs"
    item-title="text"
    item-value="value"
    variant="outlined"
    persistent-hint
    :items="selections"
  >
    <template #item="{ item, props }">
      <ListItem
        no-hover
        no-padding
        v-bind="props"
        :title="item.raw.text"
        :subtitle="item.raw.description"
      />
    </template>
    <template #append>
      <slot />
    </template>
  </VSelect>
</template>
