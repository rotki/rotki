<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import type { RoundingMode } from '@/types/settings/frontend-settings';

defineProps<{
  label: string;
  hint: string;
}>();

const { t } = useI18n();

const modelValue = defineModel<RoundingMode>({ required: true });

const selections = [
  {
    value: BigNumber.ROUND_UP,
    text: t('rounding_settings.round.up'),
    description: t('rounding_settings.round.up_description'),
  },
  {
    value: BigNumber.ROUND_DOWN,
    text: t('rounding_settings.round.down'),
    description: t('rounding_settings.round.down_description'),
  },
  {
    value: BigNumber.ROUND_HALF_EVEN,
    text: t('rounding_settings.round.half_even'),
    description: t('rounding_settings.round.half_even_description'),
  },
];
</script>

<template>
  <div class="flex gap-4 flex-start">
    <RuiMenuSelect
      v-bind="$attrs"
      v-model="modelValue"
      :options="selections"
      key-attr="value"
      text-attr="text"
      :hint="hint"
      :label="label"
      :item-height="58"
      variant="outlined"
    >
      <template #item="{ item }">
        <ListItem
          class="!py-0 !gap-0 leading-none"
          no-hover
          no-padding
          :title="item.text"
          :subtitle="item.description"
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
