<script setup lang="ts">
function reset() {
  sessionStorage.removeItem('vuex');
  window.location.reload();
}

const resetState = 'Reset State';
</script>

<template>
  <div
    id="rotki"
    class="w-full h-full"
  >
    <nav class="border-default bg-white dark:bg-black border-b flex gap-4 items-center fixed w-full p-2 top-0">
      <RouterLink :to="{ name: '/dashboard/' }">
        <RuiButton
          variant="text"
          icon
        >
          <RuiIcon name="lu-house" />
        </RuiButton>
      </RouterLink>
      <div class="grow" />
      <RuiButton
        variant="outlined"
        color="warning"
        @click="reset()"
      >
        <template #prepend>
          <RuiIcon name="lu-rotate-ccw" />
        </template>
        {{ resetState }}
      </RuiButton>
    </nav>
    <div class="w-full h-full">
      <RouterView />
    </div>
  </div>
</template>
