<template>
  <v-row no-gutters align="center">
    <v-col cols="auto" class="font-weight-medium">
      {{ capitalize(event) }}
    </v-col>
  </v-row>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { capitalize } from '@/filters';
import { EventType } from '@/services/defi/types';

export default defineComponent({
  name: 'EventTypeDisplay',
  props: {
    eventType: { required: true, type: String as PropType<EventType> }
  },
  setup(props) {
    const { eventType } = toRefs(props);

    const event = computed<string>(() => {
      return eventType.value === 'comp' ? 'comp claimed' : eventType.value;
    });

    return {
      capitalize,
      event
    };
  }
});
</script>
