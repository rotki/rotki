<template>
  <v-dialog-transition>
    <v-dialog
      v-if="display"
      :value="true"
      persistent
      max-width="500"
      class="confirm-dialog"
      @keydown.esc.stop="cancel()"
    >
      <v-card data-cy="confirm-dialog">
        <v-card-title
          class="confirm-dialog__title text-h5"
          data-cy="dialog-title"
        >
          {{ title }}
        </v-card-title>
        <v-card-text class="confirm-dialog__text">
          <v-row align="center">
            <v-col cols="auto" class="text-center">
              <v-icon :color="color" x-large>
                {{ icon }}
              </v-icon>
            </v-col>
            <v-col class="text-body-1">
              {{ message }}
              <slot />
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="confirm-dialog__actions">
          <v-spacer />
          <v-btn
            v-if="!singleAction"
            color="primary"
            depressed
            outlined
            text
            data-cy="button-cancel"
            @click="cancel()"
          >
            {{ secondaryAction }}
          </v-btn>
          <v-btn
            :color="color"
            depressed
            :disabled="disabled"
            data-cy="button-confirm"
            @click="confirm()"
          >
            {{ primaryAction }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog-transition>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { themes } from '@/components/dialogs/consts';

const ConfirmDialog = defineComponent({
  name: 'ConfirmDialog',
  props: {
    title: { required: true, type: String },
    message: { required: true, type: String },
    display: { type: Boolean, required: true },
    primaryAction: { type: String, required: false, default: 'Confirm' },
    secondaryAction: { type: String, required: false, default: 'Cancel' },
    confirmType: {
      type: String as PropType<keyof typeof themes>,
      required: false,
      default: 'info'
    },
    disabled: { type: Boolean, required: false, default: false },
    singleAction: { required: false, type: Boolean, default: false }
  },
  emits: ['confirm', 'cancel'],
  setup(props, { emit }) {
    const { confirmType } = toRefs(props);
    const color = computed(() => themes[confirmType.value].color);
    const icon = computed(() => themes[confirmType.value].icon);
    const confirm = () => emit('confirm');
    const cancel = () => emit('cancel');

    return {
      cancel,
      confirm,
      color,
      icon
    };
  }
});

export default ConfirmDialog;
</script>
<style scoped lang="scss">
.confirm-dialog {
  &__actions {
    padding: 16px !important;
  }
}
</style>
