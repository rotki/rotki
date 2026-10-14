<script setup lang="ts">
defineProps<{
  texts?: string[];
  text?: string;
}>();
</script>

<template>
  <div class="flex items-center min-w-0">
    <template v-if="texts">
      <div
        v-for="(entry, index) in texts"
        :key="entry + index"
        class="flex items-center min-w-0"
      >
        <div
          v-if="index === texts.length - 1"
          class="truncate font-medium text-rui-text"
        >
          {{ entry }}
        </div>
        <div
          v-else
          class="flex items-center shrink-0 text-rui-text-secondary"
        >
          {{ entry }}
          <RuiIcon
            class="mx-1 text-rui-text-disabled"
            size="14"
            name="lu-chevron-right"
          />
        </div>
      </div>
    </template>
    <div
      v-else
      class="truncate text-rui-text"
    >
      {{ text }}
    </div>
  </div>
</template>
