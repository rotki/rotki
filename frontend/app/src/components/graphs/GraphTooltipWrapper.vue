<script setup lang="ts">
import { type TooltipDisplayOption } from '@rotki/common/lib/settings/graphs';

withDefaults(
  defineProps<{
    tooltipOption?: TooltipDisplayOption;
  }>(),
  {
    tooltipOption: undefined
  }
);
</script>

<template>
  <div
    v-if="tooltipOption"
    :id="tooltipOption.id"
    :class="{
      [$style.tooltip]: true,
      [$style['tooltip__show']]: tooltipOption.visible
    }"
    class="bg-white dark:bg-black"
    :data-align-x="tooltipOption.xAlign"
    :data-align-y="tooltipOption.yAlign"
    :style="{
      left: `${tooltipOption.left}px`,
      top: `${tooltipOption.top}px`
    }"
  >
    <slot name="content" />
  </div>
</template>

<style module lang="scss">
.tooltip {
  position: absolute;
  opacity: 0;
  visibility: hidden;
  padding: 0.25rem 0.75rem;
  font-family: 'Roboto', sans-serif;
  font-size: 16px;
  border-radius: 6px;
  filter: drop-shadow(0 0 8px var(--v-rotki-grey-base));
  pointer-events: none;
  transition: 0.3s all;
  white-space: nowrap;
  line-height: 1.2rem;

  &__show {
    opacity: 0.9;
    visibility: visible;
  }

  &::before {
    content: '';
    width: 0;
    height: 0;
    position: absolute;
    border-width: 6px;
    border-style: solid;
    border-color: white;
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
    &:before {
      border-color: black;
    }
  }
}
</style>
