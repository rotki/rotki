<template>
  <v-dialog v-model="displayed" persistent max-width="450">
    <v-card>
      <v-card-title class="headline">
        Sync Permission Required
      </v-card-title>
      <v-layout align-center>
        <v-flex xs12>
          <v-card-text> {{ message }} </v-card-text>
        </v-flex>
      </v-layout>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn depressed color="primary" @click="confirm()">Yes</v-btn>
        <v-btn depressed @click="cancel()">No</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class SyncPermission extends Vue {
  @Prop({ required: true })
  displayed!: boolean;
  @Prop({ required: true })
  message!: string;

  @Emit()
  confirm() {}

  @Emit()
  cancel() {}
}
</script>

<style scoped></style>
