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
        <v-row align="center" class="mx-0 big-dialog__body">
          <v-col v-if="display" cols="12">
            <slot />
          </v-col>
        </v-row>
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
      </div>
    </v-card>
  </v-bottom-sheet>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { themes } from '@/components/dialogs/consts';
import { DialogThemes } from '@/components/dialogs/types';

@Component({})
export default class BigDialog extends Vue {
  @Prop({ required: true })
  title!: string;
  @Prop({ required: false })
  subtitle!: string;
  @Prop({ type: Boolean, required: true })
  display!: boolean;
  @Prop({ type: Boolean, required: false, default: false })
  loading!: boolean;
  @Prop({ type: Boolean, required: false, default: false })
  actionDisabled!: boolean;
  @Prop({ type: String, required: false, default: 'Confirm' })
  primaryAction!: string;
  @Prop({ type: String, required: false, default: 'Cancel' })
  secondaryAction!: string;
  @Prop({ type: String, required: false, default: 'info' }) // must be one of the types defined in confirmTypesProps below
  confirmType!: string;

  readonly themes: DialogThemes = themes;

  @Emit()
  confirm() {}

  @Emit()
  cancel() {}
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.big-dialog {
  height: calc(100vh - 80px);

  &__body {
    padding: 0 16px;
  }

  &__content {
    height: calc(100% - 85px);
    overflow-y: scroll;
    @extend .themed-scrollbar;
  }
}

::v-deep {
  .v-card {
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
  }
}
</style>
