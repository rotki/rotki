<script setup lang="ts">
import type { RoundingMode } from '@/types/settings/frontend-settings';
import ListItem from '@/components/common/ListItem.vue';
import { BigNumber } from '@rotki/common';

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<RoundingMode>({ required: true });

defineProps<{
  label: string;
  hint: string;
}>();

const { t } = useI18n();

const selections: { value: RoundingMode; text: string; description: string }[] = [
  {
    description: t('rounding_settings.round.up_description'),
    text: t('rounding_settings.round.up'),
    value: BigNumber.ROUND_UP,
  },
  {
    description: t('rounding_settings.round.down_description'),
    text: t('rounding_settings.round.down'),
    value: BigNumber.ROUND_DOWN,
  },
  {
    description: t('rounding_settings.round.half_even_description'),
    text: t('rounding_settings.round.half_even'),
    value: BigNumber.ROUND_HALF_EVEN,
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
          name="lu-check"
          size="24"
        />
      </template>
    </RuiMenuSelect>
    <slot />
  </div>
</template>
