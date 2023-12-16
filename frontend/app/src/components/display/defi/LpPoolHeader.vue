<template>
  <div class="flex flex-col gap-3 pt-3 pb-2">
    <div class="flex justify-between items-start gap-3">
      <div>
        <slot name="icon" />
      </div>
      <div class="-mt-3">
        <slot name="detail" />
      </div>
    </div>
    <div>
      <div class="text-subtitle-1 uppercase font-bold text-rui-text text-break mb-1">
        <slot name="name" />
      </div>
      <div>
        <slot name="hash" />
      </div>
    </div>
  </div>
</template>
