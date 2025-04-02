<script setup lang="ts">
definePage({
  name: 'playground',
});
const message = 'put your changes here';
</script>

<template>
  <div class="container text-rui-text mt-4">
    <div>{{ message }}</div>
    <!-- insert components to be tested here -->
  </div>
</template>
