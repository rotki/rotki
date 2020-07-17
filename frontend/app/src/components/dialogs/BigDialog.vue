<template>
  <v-bottom-sheet
    v-model="display"
    over
    class="big-dialog"
    width="98%"
    @click:outside="cancel()"
    @keydown.esc.stop="cancel()"
  >
    <v-card class="big-dialog">
      <v-card-title class="text-h5 big-dialog__title pt-6">
        {{ title }}
      </v-card-title>
      <v-card-subtitle v-if="subTitle">
        {{ subTitle }}
      </v-card-subtitle>
      <div class="big-dialog__content">
        <v-row align="center" class="mx-0 big-dialog__body">
          <v-col cols="12">
            <slot></slot>
          </v-col>
        </v-row>
        <v-card-actions class="px-6">
          <v-spacer></v-spacer>
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
            :color="confirmTypeProps[confirmType].color"
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

@Component({})
export default class BigDialog extends Vue {
  @Prop({ required: true })
  title!: string;
  @Prop({ required: false })
  subTitle!: string;
  @Prop({ type: Boolean, required: true })
  display!: boolean;
  @Prop({ type: String, required: false, default: 'Confirm' })
  primaryAction!: string;
  @Prop({ type: String, required: false, default: 'Cancel' })
  secondaryAction!: string;
  @Prop({ type: String, required: false, default: 'info' }) // must be one of the types defined in confirmTypesProps below
  confirmType!: string;

  confirmTypeProps = {
    info: { icon: 'fa-question-circle', color: 'primary' }, // TODO: change color: 'primary' -> 'info' when we start to use it as a variable in the new color scheme
    warning: { icon: 'fa-warning', color: 'error' },
    success: { icon: 'fa-check-circle', color: 'success' }
  };

  @Emit()
  confirm() {}

  @Emit()
  cancel() {}
}
</script>

<style scoped lang="scss">
.big-dialog {
  height: calc(100vh - 80px);

  &__body {
    padding: 0 16px;
  }

  &__content {
    height: calc(100% - 85px);
    overflow-y: scroll;
  }
}

::-webkit-scrollbar {
  width: 14px;
  height: 18px;

  &-thumb {
    height: 6px;
    border: 4px solid rgba(0, 0, 0, 0);
    background-clip: padding-box;
    border-radius: 7px;
    background-color: rgba(0, 0, 0, 0.15);
    box-shadow: inset -1px -1px 0px rgba(0, 0, 0, 0.05),
      inset 1px 1px 0px rgba(0, 0, 0, 0.05);

    &:hover {
      background-color: rgba(0, 0, 0, 0.3);
    }

    &:active {
      background-color: rgba(0, 0, 0, 0.5);
    }
  }
}
</style>
