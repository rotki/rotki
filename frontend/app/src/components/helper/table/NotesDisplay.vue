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
import { Component, Prop, Vue } from 'vue-property-decorator';
import Fragment from '@/components/helper/Fragment';

@Component({
  name: 'NotesDisplay',
  components: { Fragment }
})
export default class NotesDisplay extends Vue {
  @Prop({ required: true })
  notes!: string | null;
}
</script>
