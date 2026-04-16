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
  <div class="flex items-center text-body-2 w-full">
    <RuiIcon
      :name="icon"
      size="20"
      class="text-rui-text-secondary min-w-5"
    />
    <div
      class="ml-3 overflow-hidden py-2"
      @mouseenter="onMarqueeEnter($event)"
      @mouseleave="onMarqueeLeave($event)"
    >
      <div class="flex items-center whitespace-nowrap w-fit">
        <div
          v-for="(text, i) in texts"
          :key="i"
          class="flex items-center shrink-0"
        >
          <div v-if="i === lastIndex">
            {{ text }}
          </div>
          <div
            v-else
            class="flex items-center text-rui-text-secondary"
          >
            {{ text }}
            <RuiIcon
              class="mx-1"
              size="14"
              name="lu-chevron-right"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
