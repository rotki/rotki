<template>
  <v-dialog
    :value="display"
    persistent
    max-width="500"
    class="confirm-dialog"
    @keydown.esc.stop="cancel()"
  >
    <v-card>
      <v-card-title class="text-h5 confirm-dialog__title">
        {{ title }}
      </v-card-title>
      <v-row align="center" class="mx-0 confirm-dialog__body">
        <v-col cols="2" class="text-center">
          <v-icon :color="themes[confirmType].color" x-large>
            {{ themes[confirmType].icon }}
          </v-icon>
        </v-col>
        <v-col cols="10">
          {{ message }}
          <slot />
        </v-col>
      </v-row>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="primary"
          depressed
          outlined
          text
          class="confirm-dialog__buttons__cancel"
          @click="cancel()"
        >
          {{ secondaryAction }}
        </v-btn>
        <v-btn
          :color="themes[confirmType].color"
          depressed
          :disabled="disabled"
          class="confirm-dialog__buttons__confirm"
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
import { themes } from '@/components/dialogs/consts';
import { DialogThemes } from '@/components/dialogs/types';

@Component({})
export default class ConfirmDialog extends Vue {
  @Prop({ required: true })
  title!: string;
  @Prop({ required: true })
  message!: string;
  @Prop({ type: Boolean, required: true })
  display!: boolean;
  @Prop({ type: String, required: false, default: 'Confirm' })
  primaryAction!: string;
  @Prop({ type: String, required: false, default: 'Cancel' })
  secondaryAction!: string;
  @Prop({ type: String, required: false, default: 'info' }) // must be one of the types defined in confirmTypesProps below
  confirmType!: string;
  @Prop({ type: Boolean, required: false, default: false })
  disabled!: boolean;

  @Emit()
  confirm() {}

  @Emit()
  cancel() {}

  readonly themes: DialogThemes = themes;
}
</script>

<style scoped lang="scss">
.confirm-dialog {
  &__body {
    padding: 0 16px;
  }
}
</style>
