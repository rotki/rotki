<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import { useMarqueeAnimation } from '@/modules/shell/layout/use-marquee-animation';

const { icon, texts } = defineProps<{
  icon: RuiIcons;
  texts: string[];
}>();

const { onMarqueeEnter, onMarqueeLeave } = useMarqueeAnimation();

const lastIndex = computed<number>(() => texts.length - 1);
</script>

<template>
  <div
    class="flex items-center gap-3 text-sm w-full min-w-0"
    data-testid="settings-search-item"
  >
    <RuiIcon
      :name="icon"
      size="18"
      class="text-rui-text-secondary shrink-0"
    />
    <div
      class="overflow-hidden py-2"
      @mouseenter="onMarqueeEnter($event)"
      @mouseleave="onMarqueeLeave($event)"
    >
      <div class="flex items-center whitespace-nowrap w-fit">
        <div
          v-for="(text, i) in texts"
          :key="i"
          class="flex items-center shrink-0"
        >
          <div
            v-if="i === lastIndex"
            class="font-medium text-rui-text"
          >
            {{ text }}
          </div>
          <div
            v-else
            class="flex items-center text-rui-text-secondary"
          >
            {{ text }}
            <RuiIcon
              class="mx-1 text-rui-text-disabled"
              size="14"
              name="lu-chevron-right"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
