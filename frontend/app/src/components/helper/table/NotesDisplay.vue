<template>
  <fragment>
    <v-row>
      <v-col class="text-subtitle-2">
        {{ tc('notes_display.notes') }}
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <card outlined>
          {{ notes ? notes : tc('notes_display.empty_notes') }}
        </card>
      </v-col>
    </v-row>
  </fragment>
</template>

<script setup lang="ts">
import { PropType } from 'vue';

import Fragment from '@/components/helper/Fragment';

defineProps({
  notes: {
    required: false,
    type: String as PropType<string | null>,
    default: null
  }
});

const { tc } = useI18n();
</script>
