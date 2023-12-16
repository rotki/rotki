<script setup lang="ts">
import { contextColors } from '@rotki/ui-library';

const props = withDefaults(
  defineProps<{
    modelValue?: string;
  }>(),
  {
    modelValue: '',
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: string): void;
}>();

const vModel = useSimpleVModel(props, emit);

const { modelValue } = toRefs(props);

const contextColorsInHex: string[] = contextColors
  .map((item) => {
    const name = `--rui-light-${item}-main`;
    const points = getComputedStyle(document.documentElement).getPropertyValue(name).split(', ');
    if (points && points.length === 3)
      return rgbPointsToHex(+points[0], +points[1], +points[2]);

    return '';
  })
  .filter(item => !!item);

watchImmediate(modelValue, (value) => {
  if (!value && contextColorsInHex.length > 0)
    emit('update:model-value', contextColorsInHex[0]);
});
</script>

<template>
  <div>
    <RuiMenu
      :popper="{ placement: 'left' }"
      menu-class="max-w-[18rem]"
    >
      <template #activator="{ attrs }">
        <div
          class="rounded-full w-8 h-8 border-2 border-rui-grey-100 cursor-pointer"
          :style="{
            backgroundColor: `#${modelValue}`,
          }"
          v-bind="attrs"
        />
      </template>
      <div class="p-2 flex gap-2">
        <div
          v-for="color in contextColorsInHex"
          :key="color"
          class="rounded-full w-6 h-6 border-2 border-rui-grey-100 cursor-pointer"
          :style="{
            backgroundColor: `#${color}`,
          }"
          @click="emit('update:model-value', color)"
        />
      </div>
      <RuiColorPicker v-model="vModel" />
    </RuiMenu>
  </div>
</template>
