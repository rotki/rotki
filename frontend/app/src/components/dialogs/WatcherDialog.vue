<template>
  <v-dialog
    :value="display"
    persistent
    max-width="650"
    class="watcher-dialog"
    @keydown.esc.stop="cancel()"
  >
    <v-card>
      <v-card-title class="headline watcher-dialog__title">
        {{ title }}
      </v-card-title>
      <v-card-text>
        <v-row align="center" class="mx-0 watcher-dialog__body">
          <v-row>
            <v-col cols="12">
              {{ message }}
            </v-col>
          </v-row>
          <v-row>
            <v-col v-if="preselectWatcherType === ''" cols="12">
              <v-select
                v-model="watcherType"
                :items="watcherTypes"
                dense
                outlined
                label="Watcher Type"
                required
              >
              </v-select>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="6">
              <v-select
                v-model="watcherOperation"
                :items="watcherOperations[watcherType]"
                dense
                outlined
                :disabled="!watcherType"
                label="Operation"
                required
              >
              </v-select>
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="watcherValue"
                :label="watcherValueLabel"
                dense
                outlined
                suffix="%"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          depressed
          outlined
          text
          class="watcher-dialog__buttons__cancel"
          @click="cancel()"
        >
          {{ secondaryAction }}
        </v-btn>
        <v-btn
          depressed
          color="primary"
          class="watcher-dialog__buttons__confirm"
          @click="confirm()"
        >
          {{ primaryAction }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class WatcherDialog extends Vue {
  @Prop({ required: true })
  title!: string;
  @Prop({ required: true })
  message!: string;
  @Prop({ type: Boolean, required: true })
  display!: boolean;
  @Prop({ type: String, required: false, default: 'Add' })
  primaryAction!: string;
  @Prop({ type: String, required: false, default: 'Cancel' })
  secondaryAction!: string;

  @Prop({ required: false, default: 'Watcher Value' })
  watcherValueLabel!: string;
  @Prop({ required: true, default: null })
  watcherContentId!: string | number | null;
  @Prop({ required: false, default: '' })
  preselectWatcherType!: string;

  watcherType: string | null = null;
  watcherOperation: string | null = null;
  watcherValue: string | null = null;

  mounted() {
    this.watcherType = this.preselectWatcherType;
  }

  watcherTypes = [
    {
      text: 'Collateralization Ratio Watcher (Maker)',
      type: 'makervault_collateralization_ratio',
      value: 'makervault_collateralization_ratio'
    }
  ];

  watcherOperations = {
    makervault_collateralization_ratio: [
      { op: 'gt', value: 'gt', text: 'greater than' },
      { op: 'ge', value: 'ge', text: 'greater than or equal to' },
      { op: 'lt', value: 'lt', text: 'less than' },
      { op: 'le', value: 'le', text: 'less than or equal to' }
    ]
  };

  confirm() {
    window.alert('do api stuff');
    const watcherPaylod = {
      type: this.watcherType,
      args: {
        ratio: this.watcherValue,
        op: this.watcherOperation,
        vault_id: this.watcherContentId
      }
    };
    console.log('-----------------------');
    console.log('watcher payload');
    console.log(watcherPaylod);
    console.log('-----------------------');
    this.$emit('confirm');
  }

  @Emit()
  cancel() {}
}
</script>

<style scoped lang="scss">
.watcher-dialog__body {
  padding: 0 16px;
}
</style>
