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
  <div class="flex gap-4 items-center">
    <RuiMenuSelect
      v-bind="rootAttrs"
      :options="selections"
      key-attr="value"
      text-attr="text"
      :item-height="58"
      full-width
      show-details
      variant="outlined"
      v-on="
        // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
        $listeners
      "
    >
      <template #item.text="{ option }">
        <ListItem
          class="!py-0 !gap-0 leading-none"
          no-hover
          no-padding
          :title="option.text"
          :subtitle="option.description"
        />
      </template>
      <template #item.append="{ active }">
        <RuiIcon
          v-if="active"
          class="transition"
          name="check-line"
          size="24"
        />
      </template>
    </RuiMenuSelect>
    <slot />
  </div>
</template>
