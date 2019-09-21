<template>
  <v-dialog :value="display" persistent max-width="500" class="confirm-dialog">
    <v-card>
      <v-card-title class="headline">
        {{ title }}
      </v-card-title>
      <v-row align="center" class="mx-0 confirm-dialog__body">
        <v-col cols="1">
          <v-icon color="primary">
            fa fa-question-circle fa-3x
          </v-icon>
        </v-col>
        <v-col cols="11">
          {{ message }}
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

<style scoped lang="scss">
.confirm-dialog__body {
  padding: 0 16px;
}
</style>
