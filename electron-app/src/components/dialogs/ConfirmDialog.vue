<template>
  <v-dialog :value="display" persistent max-width="500">
    <v-card>
      <v-card-title class="headline">
        {{ title }}
      </v-card-title>
      <v-row align="center">
        <v-col cols="2">
          <v-icon class="dialog-icon" color="primary">
            fa fa-question-circle fa-3x
          </v-icon>
        </v-col>
        <v-col cols="10">
          <v-card-text> {{ message }} </v-card-text>
        </v-col>
      </v-row>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" text @click="cancel()">
          Cancel
        </v-btn>
        <v-btn color="primary" text @click="confirm()">
          Confirm
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ConfirmDialog extends Vue {
  @Prop({ required: true })
  title!: string;
  @Prop({ required: true })
  message!: string;
  @Prop({ type: Boolean, required: true })
  display!: boolean;

  @Emit()
  confirm() {}

  @Emit()
  cancel() {}
}
</script>

<style scoped>
.dialog-icon {
  margin-left: 25px;
}
</style>
