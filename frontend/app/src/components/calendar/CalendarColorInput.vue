<script setup lang="ts">
import { contextColors } from '@rotki/ui-library-compat';

const props = withDefaults(
  defineProps<{
    value?: string;
  }>(),
  {
    value: '',
  },
);

const emit = defineEmits<{
  (e: 'input', value: string): void;
}>();

const { value } = toRefs(props);

const contextColorsInHex: string[] = contextColors.map((item) => {
  const name = `--rui-light-${item}-main`;
  const points = getComputedStyle(document.documentElement).getPropertyValue(name).split(', ');
  if (points && points.length === 3)
    return rgbPointsToHex(+points[0], +points[1], +points[2]);

  return '';
}).filter(item => !!item);

watchImmediate(value, (value) => {
  if (!value && contextColorsInHex.length > 0)
    emit('input', contextColorsInHex[0]);
});
</script>

<template>
  <div>
    <RuiMenu
      :popper="{ placement: 'left' }"
    >
      <template #activator="{ on }">
        <div
          class="rounded-full w-8 h-8 border-2 border-rui-grey-100 cursor-pointer"
          :style="{
            backgroundColor: `#${value}`,
          }"
          v-on="on"
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
          @click="emit('input', color)"
        />
      </div>
      <AppBridge>
        <VColorPicker
          class="rounded-none"
          hide-mode-switch
          mode="hexa"
          :value="`#${value}`"
          @update:color="
            emit('input', $event.hex.replace('#', ''))
          "
        />
      </AppBridge>
    </RuiMenu>
  </div>
</template>
