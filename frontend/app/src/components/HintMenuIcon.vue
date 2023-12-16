<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

withDefaults(
  defineProps<{
    text?: string;
    menuClass?: string | string[] | Record<string, boolean>;
    maxWidth?: string;
  }>(),
  {
    text: undefined,
    maxWidth: '25rem',
    menuClass: undefined,
  },
);

const visible = ref(false);
const attrs = useAttrs();
</script>

<template>
  <VMenu
    v-model="visible"
    offset-x
    :max-width="maxWidth"
    v-bind="attrs"
  >
    <template #activator="{ props }">
      <RuiButton
        variant="text"
        icon
        v-bind="props"
        @click="visible = true"
      >
        <RuiIcon name="question-line" />
      </RuiButton>
    </template>
    <div
      class="p-4"
      :class="menuClass"
    >
      <slot> {{ text }} </slot>
    </div>
  </VMenu>
</template>
