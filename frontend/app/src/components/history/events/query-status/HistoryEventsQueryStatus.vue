<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    colspan: number;
    locations?: string[];
  }>(),
  {
    locations: () => []
  }
);

const { locations } = toRefs(props);

const openStatusDropdown = ref<boolean>(false);

const store = useEventsQueryStatusStore();
const { isAllFinished } = toRefs(store);

const { sortedQueryStatus, length } = useEventsQueryStatus(locations);

const { isStatusFinished, resetQueryStatus } = store;

const css = useCssModule();
const { locationData } = useLocations();
</script>

<template>
  <tr v-if="length > 0" :class="css.tr">
    <td :colspan="colspan" class="py-2">
      <div class="d-flex">
        <div v-if="isAllFinished" class="pr-2">
          <v-btn icon @click="resetQueryStatus()">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <div class="pr-2">
          <v-btn
            v-if="length > 1 && !isAllFinished"
            icon
            @click="openStatusDropdown = !openStatusDropdown"
          >
            <v-icon v-if="openStatusDropdown"> mdi-chevron-up </v-icon>
            <v-icon v-else> mdi-chevron-down </v-icon>
          </v-btn>
        </div>
        <div>
          <div
            v-if="isAllFinished || (!openStatusDropdown && length > 1)"
            class="py-2 d-flex align-center"
          >
            <div class="mr-4">
              <v-progress-circular
                v-if="!isAllFinished"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <v-icon v-else color="green" :class="css['check-icon']">
                mdi-check-circle
              </v-icon>
            </div>
            <history-events-query-status-current :locations="locations" />
          </div>
          <div
            v-for="item in sortedQueryStatus"
            v-else
            :key="item.location + item.name"
            class="d-flex align-center"
          >
            <div class="mr-4">
              <v-progress-circular
                v-if="!isStatusFinished(item)"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <v-icon v-else color="green" :class="css['check-icon']">
                mdi-check-circle
              </v-icon>
            </div>

            <location-icon
              icon
              no-padding
              :item="locationData(item.location)"
              size="20px"
            />

            <history-events-query-status-line :item="item" class="ms-2" />
          </div>
        </div>
        <v-spacer />
        <history-events-query-status-dialog :locations="locations" />
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
