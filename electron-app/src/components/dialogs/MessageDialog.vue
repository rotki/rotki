<template>
  <v-dialog v-model="visible" persistent max-width="500">
    <v-card>
      <v-card-title
        :class="{ 'green--text': success, 'red--text': !success }"
        class="headline"
      >
        {{ title }}
      </v-card-title>
      <v-layout align-center>
        <v-flex xs2>
          <v-icon
            class="dialog-icon"
            :class="{ 'green--text': success, 'red--text': !success }"
          >
            fa {{ success ? 'fa-check-circle' : 'fa-exclamation-circle' }} fa-3x
          </v-icon>
        </v-flex>
        <v-flex xs10>
          <v-card-text class="message-dialog__message">
            {{ message }}
          </v-card-text>
        </v-flex>
      </v-layout>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn :color="success ? 'green' : 'red'" text @click="dismiss()">
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
.dialog-icon {
  margin-left: 25px;
}

.message-dialog__message {
  overflow-wrap: break-word;
  word-wrap: break-word;
  hyphens: auto;
}
</style>
