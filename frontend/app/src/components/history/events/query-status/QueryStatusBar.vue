<script setup lang="ts">
defineProps<{
  colspan: number;
  finished: boolean;
  items: any[];
  getKey: (item: any) => string;
  isItemFinished: (item: any) => boolean;
}>();

const openStatusDropdown = ref<boolean>(false);

const emit = defineEmits<{ (e: 'reset'): void }>();

const css = useCssModule();
</script>

<template>
  <tr v-if="items.length > 0" :class="css.tr">
    <td :colspan="colspan" class="py-2">
      <div class="d-flex">
        <div v-if="finished" class="pr-2">
          <v-btn icon @click="emit('reset')">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <div class="pr-2">
          <v-btn
            v-if="items.length > 1 && !finished"
            icon
            @click="openStatusDropdown = !openStatusDropdown"
          >
            <v-icon v-if="openStatusDropdown"> mdi-chevron-up </v-icon>
            <v-icon v-else> mdi-chevron-down </v-icon>
          </v-btn>
        </div>
        <div>
          <div
            v-if="finished || (!openStatusDropdown && items.length > 1)"
            class="py-2 d-flex align-center"
          >
            <div class="mr-4">
              <v-progress-circular
                v-if="!finished"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <v-icon v-else color="green" :class="css['check-icon']">
                mdi-check-circle
              </v-icon>
            </div>

            <slot name="current" />
          </div>
          <div
            v-for="item in items"
            v-else
            :key="getKey(item)"
            class="d-flex align-center"
          >
            <div class="mr-4">
              <v-progress-circular
                v-if="!isItemFinished(item)"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <v-icon v-else color="green" :class="css['check-icon']">
                mdi-check-circle
              </v-icon>
            </div>

            <slot name="item" :item="item" />
          </div>
        </div>
        <v-spacer />
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
