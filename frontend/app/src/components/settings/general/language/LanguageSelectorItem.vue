<template>
  <div class="d-flex align-center">
    <div class="ml-1 d-flex align-center">
      <div
        v-for="(country, index) in countries"
        :key="country"
        class="d-flex align-center"
      >
        <span v-if="index > 0" class="px-1">/</span>
        <span :class="!dense ? $style['big-flag'] : null">
          {{ getFlagEmoji(country) }}
        </span>
      </div>
    </div>
    <div v-if="showLabel" class="ml-3">
      {{ label }}
    </div>
  </div>
</template>
<script setup lang="ts">
import { PropType } from 'vue';

defineProps({
  countries: {
    required: true,
    type: Array as PropType<string[]>
  },
  dense: {
    required: false,
    type: Boolean,
    default: false
  },
  label: {
    required: true,
    type: String
  },
  showLabel: {
    required: false,
    type: Boolean,
    default: true
  }
});

const getFlagEmoji = (code: string) => {
  const codePoints = code
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
};
</script>

<style lang="scss" module>
.big-flag {
  font-size: 1.5rem;
}
</style>
