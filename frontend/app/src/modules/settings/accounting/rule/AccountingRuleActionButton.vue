<script setup lang="ts">
defineProps<{
  icon: string;
  title: string;
  subtitle: string;
}>();

const emit = defineEmits<{
  click: [];
}>();
</script>

<template>
  <RuiButton
    variant="outlined"
    color="primary"
    class="w-full justify-start"
    @click="emit('click')"
  >
    <template #prepend>
      <RuiIcon
        size="20"
        :name="icon"
      />
    </template>
    <div class="text-left ml-1">
      <div>{{ title }}</div>
      <div class="text-xs text-rui-text-secondary mb-1">
        {{ subtitle }}
      </div>
    </div>
  </RuiButton>
</template>
