<script setup lang="ts">
defineProps<{
  countries: string[];
  label: string;
}>();

function getFlagEmoji(code: string) {
  const codePoints = code
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}
</script>

<template>
  <div class="flex items-center">
    <div class="ml-1 flex items-center">
      <div
        v-for="(country, index) in countries"
        :key="country"
        class="flex items-center"
      >
        <span
          v-if="index > 0"
          class="px-1"
        >
          /
        </span>
        <span :class="$style.flag">
          {{ getFlagEmoji(country) }}
        </span>
      </div>
    </div>
    <div class="ml-3">
      {{ label }}
    </div>
  </div>
</template>

<style lang="scss" module>
.flag {
  font-size: 1.5rem;
}
</style>
