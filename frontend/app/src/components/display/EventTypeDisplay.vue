<template>
  <v-row no-gutters align="center">
    <v-col cols="auto" class="font-weight-medium">
      {{ event | capitalize }}
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { EventType } from '@/services/defi/types';

@Component({})
export default class EventTypeDisplay extends Vue {
  @Prop({ required: true })
  eventType!: EventType;

  get event(): string {
    if (this.eventType === 'comp') {
      return `comp claimed`;
    }
    return this.eventType;
  }
}
</script>

<style scoped></style>
