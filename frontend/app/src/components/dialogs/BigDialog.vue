<template>
  <v-bottom-sheet
    :value="display"
    v-bind="$attrs"
    over
    class="big-dialog"
    width="98%"
    @click:outside="cancel()"
    @keydown.esc.stop="cancel()"
    @input="cancel"
  >
    <v-card class="big-dialog" data-cy="bottom-dialog">
      <v-card-title>
        <card-title>
          {{ title }}
        </card-title>
      </v-card-title>
      <v-card-subtitle v-if="subtitle">
        {{ subtitle }}
      </v-card-subtitle>
      <div class="big-dialog__content">
        <div class="big-dialog__body">
          <slot v-if="display" />
        </div>
      </div>
      <v-card-actions class="px-6">
        <v-progress-linear v-if="loading" indeterminate class="mx-4" />
        <v-spacer />
        <v-btn
          color="primary"
          depressed
          outlined
          text
          class="big-dialog__buttons__cancel"
          @click="cancel()"
        >
          {{ secondaryAction }}
        </v-btn>
        <v-btn
          data-cy="confirm"
          :color="themes[confirmType].color"
          :disabled="actionDisabled"
          depressed
          class="big-dialog__buttons__confirm"
          @click="confirm()"
        >
          {{ primaryAction }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-bottom-sheet>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { DIALOG_TYPES, themes, TYPE_INFO } from '@/components/dialogs/consts';

export default defineComponent({
  name: 'BigDialog',
  props: {
    title: { required: true, type: String },
    subtitle: { required: false, type: String, default: '' },
    display: { required: true, type: Boolean },
    loading: { required: false, type: Boolean, default: false },
    actionDisabled: { required: false, type: Boolean, default: false },
    primaryAction: { required: false, type: String, default: 'Confirm' },
    secondaryAction: { required: false, type: String, default: 'Cancel' },
    confirmType: {
      required: false,
      type: String as PropType<typeof DIALOG_TYPES[number]>,
      default: TYPE_INFO
    }
  },
  emits: ['confirm', 'cancel'],
  setup(_, { emit }) {
    const confirm = () => emit('confirm');

    const cancel = () => emit('cancel');

    return {
      themes,
      confirm,
      cancel
    };
  }
});
</script>

<style scoped lang="scss">
.big-dialog {
  height: calc(100vh - 80px);

  &__body {
    padding: 0 1.5rem;
  }

  &__content {
    max-height: calc(100% - 120px);
    overflow-y: auto;
  }
}

::v-deep {
  .v-card {
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;

    &__actions {
      padding: 1rem 1.5rem !important;
    }
  }
}
</style>
