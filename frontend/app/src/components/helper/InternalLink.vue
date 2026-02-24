<script lang="ts" setup>
import type { RouteLocationRaw } from 'vue-router';

defineOptions({
  inheritAttrs: false,
});

const { to, activeClass = '', exactActiveClass = '', replace = false } = defineProps<{
  to: RouteLocationRaw;
  activeClass?: string;
  exactActiveClass?: string;
  replace?: boolean;
}>();

defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <RouterLink
    #default="{ href, navigate, isActive, isExactActive }"
    custom
    :to="to"
    :replace="replace"
    :active-class="activeClass"
    :exact-active-class="exactActiveClass"
  >
    <a
      :class="{
        [`${activeClass}`]: isActive,
        [`${exactActiveClass}`]: isExactActive,
      }"
      :href="href"
      v-bind="$attrs"
      @click.exact="navigate($event)"
      @click.meta.prevent
      @click.ctrl.prevent
      @click.shift.prevent
    >
      <RuiButton
        variant="text"
        color="primary"
        class="!inline !text-[1em] !p-0 !px-0.5 !-mx-0.5 !font-[inherit] [&_span]:underline"
      >
        <slot />
      </RuiButton>
    </a>
  </RouterLink>
</template>
