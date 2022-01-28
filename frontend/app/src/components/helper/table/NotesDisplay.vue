<template>
  <fragment>
    <v-row>
      <v-col class="text-subtitle-2">
        {{ $t('notes_display.notes') }}
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <card outlined>
          {{ notes ? notes : $t('notes_display.empty_notes') }}
        </card>
      </v-col>
    </v-row>
  </fragment>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import Fragment from '@/components/helper/Fragment';

export default defineComponent({
  name: 'NotesDisplay',
  components: { Fragment },
  props: {
    notes: { required: false, type: String, default: '' }
  }
});
</script>
