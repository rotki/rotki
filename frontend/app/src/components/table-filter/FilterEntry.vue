<script setup lang="ts">
import type { SearchMatcher } from '@/types/filtering';

defineProps<{
  matcher: SearchMatcher<any>;
  active: boolean;
}>();

const emit = defineEmits<{
  (e: 'click', matcher: SearchMatcher<any>): void;
}>();

function click(matcher: SearchMatcher<any>) {
  emit('click', matcher);
}
</script>

<template>
  <RuiButton
    variant="text"
    class="text-body-1 tracking-wide w-full justify-start text-left text-rui-text-secondary [&>span]:overflow-hidden [&>span]:text-ellipsis"
    :class="{
      '!bg-rui-primary-lighter/20': active,
    }"
    @click="click(matcher)"
  >
    <span class="font-medium text-rui-primary"> {{ matcher.key }}: </span>
    <span
      class="ml-1 font-normal"
      :title="matcher.description"
    >
      {{ matcher.description }}
    </span>
  </RuiButton>
</template>
