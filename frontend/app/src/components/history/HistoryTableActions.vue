<template>
  <div class="flex flex-row items-center flex-wrap gap-2 mb-4">
    <slot />
    <div class="grow xs:hidden md:block" />
    <div class="md:w-[350px] w-full lg:w-[400px]">
      <slot name="filter" />
    </div>
  </div>
</template>
