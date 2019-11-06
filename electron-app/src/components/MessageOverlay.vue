<template>
  <v-overlay v-if="visible" class="messsage-overlay">
    <v-card light max-width="500" class="mx-auto">
      <v-card-title>
        <slot name="title"></slot>
      </v-card-title>
      <v-card-text>
        <v-row class="mx-auto text-justify">
          <v-col cols="2" align-self="center">
            <v-icon color="success" size="60">
              fa fa-info-circle
            </v-icon>
          </v-col>
          <v-col cols="10">
            <slot></slot>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <div class="flex-grow-1"></div>
        <v-btn
          v-if="action"
          text
          color="primary"
          class="message-overlay__buttons__confirm"
          depressed
          @click="$emit('primary')"
        >
          {{ action }}
        </v-btn>
        <v-btn
          class="message-overlay__buttons__cancel"
          text
          @click="$emit('close')"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-overlay>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { Version } from '@/store/store';

@Component({})
export default class MessageOverlay extends Vue {
  version!: Version;

  @Prop({ required: true, type: Boolean })
  visible!: boolean;
  @Prop({ type: String })
  action!: string;
}
</script>
<style scoped lang="scss">
.message-overlay__icon {
  padding: 8px;
}
</style>
