<script setup lang="ts">
defineProps<{
  text?: string;
  menuClass?: string | string[] | Record<string, boolean>;
}>();

const visible = ref(false);
const attrs = useAttrs();
</script>

<template>
  <VMenu v-model="visible" v-bind="attrs" offset-x>
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
