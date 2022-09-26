<template>
  <card class="mt-8">
    <template #title><slot name="title" /></template>
    <template v-if="$slots.subtitle" #subtitle>
      <slot name="subtitle" />
    </template>
    <template #default>
      <slot />
    </template>
  </card>
</template>
