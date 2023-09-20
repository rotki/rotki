<script setup lang="ts">
defineProps<{
  colspan: number;
  finished: boolean;
  items: any[];
  getKey: (item: any) => string;
  isItemFinished: (item: any) => boolean;
}>();

const emit = defineEmits<{ (e: 'reset'): void }>();

const openStatusDropdown = ref<boolean>(false);

const css = useCssModule();
</script>

<template>
  <tr v-if="items.length > 0" :class="css.tr">
    <td :colspan="colspan" class="py-2">
      <div class="flex">
        <div v-if="finished" class="pr-2">
          <VBtn icon @click="emit('reset')">
            <VIcon>mdi-close</VIcon>
          </VBtn>
        </div>
        <div class="pr-2">
          <VBtn
            v-if="items.length > 1 && !finished"
            icon
            @click="openStatusDropdown = !openStatusDropdown"
          >
            <VIcon v-if="openStatusDropdown"> mdi-chevron-up </VIcon>
            <VIcon v-else> mdi-chevron-down </VIcon>
          </VBtn>
        </div>
        <div>
          <div
            v-if="finished || (!openStatusDropdown && items.length > 1)"
            class="py-2 flex items-center"
          >
            <div class="mr-4">
              <VProgressCircular
                v-if="!finished"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <VIcon v-else color="green" :class="css['check-icon']">
                mdi-check-circle
              </VIcon>
            </div>

            <slot name="current" />
          </div>
          <div
            v-for="item in items"
            v-else
            :key="getKey(item)"
            class="flex items-center"
          >
            <div class="mr-4">
              <VProgressCircular
                v-if="!isItemFinished(item)"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <VIcon v-else color="green" :class="css['check-icon']">
                mdi-check-circle
              </VIcon>
            </div>

            <slot name="item" :item="item" />
          </div>
        </div>
        <VSpacer />
        <slot name="dialog" />
      </div>
    </td>
  </tr>
</template>

<style module lang="scss">
.tr {
  background: transparent !important;
}

.row {
  display: flex;
}

.check-icon {
  margin: -2px;
}
</style>
