<template>
  <div
    v-if="tooltipOption"
    :id="tooltipOption.id"
    :class="{
      [$style.tooltip]: true,
      [$style['tooltip__dark']]: dark,
      [$style['tooltip__show']]: tooltipOption.visible
    }"
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
<script setup lang="ts">
import { TooltipDisplayOption } from '@rotki/common/lib/settings/graphs';
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';

defineProps({
  tooltipOption: {
    required: false,
    type: Object as PropType<TooltipDisplayOption>,
    default: null
  }
});

const { dark } = useTheme();
</script>
<style module lang="scss">
.tooltip {
  position: absolute;
  opacity: 0;
  visibility: hidden;
  background-color: white;
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

  &__dark {
    color: black;
  }

  &::before {
    content: '';
    width: 0;
    height: 0;
    position: absolute;
    border-width: 6px;
    border-style: solid;
    border-color: transparent;
  }

  &[data-align-x='left'],
  &[data-align-x='right'] {
    &::before {
      border-top-color: transparent;
      border-bottom-color: transparent;
    }
  }

  &[data-align-x='left'] {
    &::before {
      border-right-color: white;
      right: 100%;
    }

    &:not([data-align-y='center']) {
      &::before {
        border-right-color: transparent;
        right: calc(100% - 16px);
      }
    }
  }

  &[data-align-x='right'] {
    &::before {
      border-left-color: white;
      left: 100%;
    }

    &:not([data-align-y='center']) {
      &::before {
        border-left-color: transparent;
        left: calc(100% - 16px);
      }
    }
  }

  &[data-align-y='top'],
  &[data-align-y='bottom'] {
    &::before {
      border-left-color: transparent;
      border-right-color: transparent;
    }
  }

  &[data-align-y='top'] {
    &::before {
      border-bottom-color: white;
      bottom: 100%;
    }
  }

  &[data-align-y='bottom'] {
    &::before {
      border-top-color: white;
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
</style>
