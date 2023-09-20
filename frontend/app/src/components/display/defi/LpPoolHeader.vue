<template>
  <div class="flex justify-between pt-4 pb-2">
    <div>
      <div class="mb-3">
        <slot name="icon" />
      </div>
      <div>
        <div
          class="text-subtitle-1 text-uppercase font-bold text-rui-text text-break mb-1"
        >
          <slot name="name" />
        </div>
        <div>
          <slot name="hash" />
        </div>
      </div>
    </div>
    <div class="ml-3">
      <slot name="detail" />
    </div>
  </div>
</template>
