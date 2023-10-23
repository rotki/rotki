<script setup lang="ts">
defineOptions({
  inheritAttrs: false
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
    menuClass: undefined
  }
);

const visible = ref(false);
const attrs = useAttrs();
</script>

<template>
  <VMenu v-model="visible" offset-x :max-width="maxWidth" v-bind="attrs">
    <template #activator="{ on }">
      <RuiButton variant="text" icon @click="visible = true" v-on="on">
        <RuiIcon name="question-line" />
      </RuiButton>
    </template>
    <div class="pa-4" :class="menuClass">
      <slot> {{ text }} </slot>
    </div>
  </VMenu>
</template>
