<template>
  <badge-display>
    {{ event }}
  </badge-display>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import { EventType } from '@/services/defi/types';

export default defineComponent({
  name: 'EventTypeDisplay',
  components: { BadgeDisplay },
  props: {
    eventType: { required: true, type: String as PropType<EventType> }
  },
  setup(props) {
    const { eventType } = toRefs(props);

    const event = computed<string>(() => {
      return get(eventType) === 'comp' ? 'comp claimed' : get(eventType);
    });

    return {
      event
    };
  }
});
</script>
