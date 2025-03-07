<script setup lang="ts">
import type { TooltipDisplayOption } from '@rotki/common';

withDefaults(
  defineProps<{
    tooltipOption?: TooltipDisplayOption;
  }>(),
  {
    tooltipOption: undefined,
  },
);

defineSlots<{
  content: () => any;
}>();
</script>

<template>
  <div
    v-if="tooltipOption"
    :id="tooltipOption.id"
    :class="[
      $style.tooltip,
      {
        [$style.tooltip__show]: tooltipOption.visible,
      },
    ]"
    class="bg-white dark:bg-black"
    :data-align-x="tooltipOption.xAlign"
    :data-align-y="tooltipOption.yAlign"
    :style="{
      left: `${tooltipOption.left}px`,
      top: `${tooltipOption.top}px`,
    }"
  >
    <slot name="content" />
  </div>
</template>

<style module lang="scss">
.tooltip {
  @apply absolute opacity-0 invisible py-1 px-3 rounded-md pointer-events-none transition-all duration-300 whitespace-nowrap leading-5;
  filter: drop-shadow(0 0 0.5rem rgba(var(--rui-grey-400)));

  &__show {
    @apply opacity-90 visible;
  }

  &::before {
    @apply absolute border-[6px] border-white w-0 h-0;
    content: '';
  }

  &[data-align-x='left'],
  &[data-align-x='right'] {
    &::before {
      border-top-color: transparent !important;
      border-bottom-color: transparent !important;
    }
  }

  &[data-align-x='left'] {
    &::before {
      border-left-color: transparent !important;
      right: 100%;
    }

    &:not([data-align-y='center']) {
      &::before {
        border-right-color: transparent !important;
        right: calc(100% - 16px);
      }
    }
  }

  &[data-align-x='right'] {
    &::before {
      border-right-color: transparent !important;
      left: 100%;
    }

    &:not([data-align-y='center']) {
      &::before {
        border-left-color: transparent !important;
        left: calc(100% - 16px);
      }
    }
  }

  &[data-align-y='top'],
  &[data-align-y='bottom'] {
    &::before {
      border-left-color: transparent !important;
      border-right-color: transparent !important;
    }
  }

  &[data-align-y='top'] {
    &::before {
      border-top-color: transparent !important;
      bottom: 100%;
    }
  }

  &[data-align-y='bottom'] {
    &::before {
      border-bottom-color: transparent !important;
      top: 100%;
    }
  }

  &[data-align-x='center'] {
    &::before {
      left: 50%;
      transform: translateX(-50%);
    }
  }

  &[data-align-y='center'] {
    &::before {
      top: 50%;
      transform: translateY(-50%);
    }
  }
}

:global(.dark) {
  .tooltip {
    filter: drop-shadow(0 0 0.5rem rgba(var(--rui-grey-800)));

    &:before {
      border-color: black;
    }
  }
}
</style>
