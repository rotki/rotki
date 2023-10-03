<script setup lang="ts">
withDefaults(
  defineProps<{
    tooltip: string;
    onMenu?: object;
    retainFocusOnClick?: boolean;
    className?: string;
    href?: string;
  }>(),
  {
    onMenu: undefined,
    retainFocusOnClick: false,
    className: '',
    href: undefined
  }
);

const emit = defineEmits<{
  (e: 'click'): void;
}>();

const click = () => emit('click');
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'bottom' }"
    open-delay="250"
    close-delay="0"
  >
    <template #activator>
      <RuiButton
        variant="text"
        icon
        :href="href"
        :tag="href ? 'a' : 'button'"
        target="_blank"
        :class="className"
        class="!w-12 !h-12"
        :retain-focus-on-click="retainFocusOnClick"
        @click="click()"
        v-on="onMenu"
      >
        <slot />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </RuiTooltip>
</template>
