<script setup lang="ts">
import { type SearchMatcher } from '@/types/filtering';

defineProps<{
  matcher: SearchMatcher<any>;
  active: boolean;
}>();

const emit = defineEmits<{
  (e: 'click', matcher: SearchMatcher<any>): void;
}>();

const click = (matcher: SearchMatcher<any>) => {
  emit('click', matcher);
};

const css = useCssModule();
</script>

<template>
  <RuiButton
    variant="text"
    class="text-body-1 tracking-wide w-full justify-start text-left text-rui-text-secondary"
    :class="{
      [css.selected]: active
    }"
    @click="click(matcher)"
  >
    <span class="font-medium text-rui-primary"> {{ matcher.key }}: </span>
    <span class="ml-1 font-normal">
      {{ matcher.description }}
    </span>
  </RuiButton>
</template>

<style lang="scss" module>
.selected {
  @apply bg-rui-primary-lighter/20 #{!important};
}
</style>
