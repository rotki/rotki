<template>
  <v-dialog v-model="display" persistent max-width="400">
    <v-card>
      <v-card-title class="headline">
        {{ title }}
      </v-card-title>
      <v-layout align-center>
        <v-flex xs2>
          <v-icon class="dialog-icon" color="primary">
            fa fa-question-circle fa-3x
          </v-icon>
        </v-flex>
        <v-flex xs10>
          <v-card-text> {{ message }} </v-card-text>
        </v-flex>
      </v-layout>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" flat @click="cancel()">
          Cancel
        </v-btn>
        <v-btn color="primary" flat @click="confirm()">
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
  @Prop({ required: true })
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
