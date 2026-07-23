<script setup lang="ts">
defineProps<{
  texts?: string[];
  text?: string;
}>();
</script>

<template>
  <div class="ml-3 flex items-center">
    <template v-if="texts">
      <div
        v-for="(entry, index) in texts"
        :key="entry + index"
        class="flex items-center"
      >
        <div v-if="index === texts.length - 1">
          {{ entry }}
        </div>
        <div
          v-else
          class="flex items-center text-rui-text-secondary"
        >
          {{ entry }}
          <RuiIcon
            class="d-inline mx-2"
            size="16"
            name="lu-chevron-right"
          />
        </div>
      </div>
    </template>
    <template v-else>
      {{ text }}
    </template>
  </div>
</template>
