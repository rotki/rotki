<script setup lang="ts">
import { rgbPointsToHex } from '@rotki/common';

const model = defineModel<string | undefined>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const contextColorsInHex: string[] = contextColors
  .map((item) => {
    const name = `--rui-light-${item}-main`;
    const points = getComputedStyle(document.documentElement).getPropertyValue(name).split(', ');
    if (points && points.length === 3)
      return rgbPointsToHex(+points[0], +points[1], +points[2]);

    return '';
  })
  .filter(item => !!item);

watchImmediate(model, (value) => {
  if (!value && contextColorsInHex.length > 0)
    updateModel(contextColorsInHex[0]);
});

function updateModel(newValue: string) {
  set(model, newValue);
}
</script>

<template>
  <RuiMenu
    class="flex"
    :options="{ placement: 'bottom-start' }"
    :class-names="{ menu: 'max-w-72' }"
  >
    <template #activator="{ attrs }">
      <button
        type="button"
        class="size-5 shrink-0 cursor-pointer rounded-full ring-1 ring-rui-divider focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rui-primary"
        :style="{ backgroundColor: `#${model}` }"
        :aria-label="t('calendar.dialog.color')"
        data-testid="calendar-form-color"
        v-bind="attrs"
      />
    </template>
    <div class="flex gap-2 p-3 pb-0">
      <button
        v-for="color in contextColorsInHex"
        :key="color"
        type="button"
        class="size-6 cursor-pointer rounded-full ring-1 ring-rui-divider focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rui-primary"
        :class="{ 'ring-2 ring-offset-2 ring-rui-text': color === model }"
        :style="{ backgroundColor: `#${color}` }"
        :aria-label="`#${color}`"
        @click="updateModel(color)"
      />
    </div>
    <RuiColorPicker v-model="model" />
  </RuiMenu>
</template>
