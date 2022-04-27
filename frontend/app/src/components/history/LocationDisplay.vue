<template>
  <navigator-link :enabled="opensDetails" :to="route" component="div">
    <list-item
      v-bind="$attrs"
      class="my-0 text-center"
      :show-details="false"
      :title="location.name"
    >
      <template #icon>
        <location-icon
          class="location-display"
          :item="location"
          :icon="icon"
          :size="size"
        />
      </template>
    </list-item>
  </navigator-link>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import ListItem from '@/components/helper/ListItem.vue';
import NavigatorLink from '@/components/helper/NavigatorLink.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocationData } from '@/components/history/type';
import { setupLocationInfo } from '@/composables/balances';
import { Routes } from '@/router/routes';
import { TradeLocation } from '@/services/history/types';

export default defineComponent({
  name: 'LocationDisplay',
  components: { NavigatorLink, ListItem, LocationIcon },
  props: {
    identifier: { required: true, type: String as PropType<TradeLocation> },
    icon: { required: false, type: Boolean, default: false },
    size: { required: false, type: String, default: '24px' },
    opensDetails: { required: false, type: Boolean, default: true }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const { getLocation } = setupLocationInfo();

    const location = computed<TradeLocationData>(() =>
      getLocation(get(identifier))
    );

    const route = {
      path: Routes.LOCATIONS.route.replace(
        ':identifier',
        get(location).identifier
      )
    };

    return {
      location,
      route
    };
  }
});
</script>

<style scoped lang="scss">
.location-display {
  width: 100%;
}
</style>
