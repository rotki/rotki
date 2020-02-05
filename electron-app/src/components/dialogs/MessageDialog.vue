<template>
  <v-dialog v-model="visible" persistent max-width="500" class="message-dialog">
    <v-card>
      <v-card-title
        :class="{ 'green--text': success, 'red--text': !success }"
        class="headline message-dialog__title"
      >
        {{ title }}
      </v-card-title>
      <v-row align="center" class="mx-0 message-dialog__body">
        <v-col cols="1">
          <v-icon
            size="40"
            class="dialog-icon"
            :class="{ 'green--text': success, 'red--text': !success }"
          >
            fa {{ success ? 'fa-check-circle' : 'fa-exclamation-circle' }}
          </v-icon>
        </v-col>
        <v-col cols="11">
          <v-card-text class="message-dialog__message">
            {{ message }}
          </v-card-text>
        </v-col>
      </v-row>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          :color="success ? 'green' : 'red'"
          text
          class="message-dialog__buttons__confirm"
          @click="dismiss()"
        >
          Ok
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';

@Component({})
export default class MessageDialog extends Vue {
  @Prop({ required: true })
  title!: string;
  @Prop({ required: true })
  message!: string;
  @Prop({ default: false, type: Boolean })
  success!: boolean;

  visible: boolean = false;

  @Watch('message')
  onMessage() {
    this.visible = this.message.length > 0;
  }

  @Emit()
  dismiss() {}
}
</script>

<style scoped>
.message-dialog__message {
  overflow-wrap: break-word;
  word-wrap: break-word;
  hyphens: auto;
}

.message-dialog__body {
  padding: 0 16px;
}
</style>
