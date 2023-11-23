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
      <div class="flex items-start gap-3">
        <RuiButton
          v-if="finished"
          class="mt-0.5"
          size="sm"
          icon
          variant="text"
          @click="emit('reset')"
        >
          <RuiIcon name="close-line" />
        </RuiButton>
        <RuiButton
          v-else-if="items.length > 1 && !finished"
          class="mt-0.5"
          icon
          size="sm"
          variant="text"
          @click="openStatusDropdown = !openStatusDropdown"
        >
          <RuiIcon v-if="openStatusDropdown" name="arrow-up-s-line" />
          <RuiIcon v-else name="arrow-down-s-line" />
        </RuiButton>

        <div
          v-if="finished || (!openStatusDropdown && items.length > 1)"
          class="py-2 flex items-center gap-3"
        >
          <div class="flex">
            <RuiProgress
              v-if="!finished"
              color="primary"
              size="20"
              thickness="2"
              variant="indeterminate"
              circular
            />

            <SuccessDisplay v-else size="20" success />
          </div>

          <slot name="current" />
        </div>
        <div v-else>
          <div
            v-for="item in items"
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
</style>
