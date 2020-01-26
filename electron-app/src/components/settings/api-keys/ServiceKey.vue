<template>
  <v-card>
    <v-card-title>
      {{ title }}
    </v-card-title>
    <v-card-text class="service-key__content">
      <revealable-input
        :value="value"
        class="service-key__api-key"
        :hint="value ? '' : hint"
        :label="label"
        @input="input"
      ></revealable-input>
      <v-tooltip top>
        <template #activator="{ on }">
          <v-btn
            icon
            text
            class="service-key__content__delete"
            :disabled="loading || !value"
            color="primary"
            v-on="on"
            @click="deleteKey()"
          >
            <v-icon>fa-trash</v-icon>
          </v-btn>
        </template>
        <span>
          {{ tooltip }}
        </span>
      </v-tooltip>
    </v-card-text>
    <v-card-actions>
      <v-btn
        class="service-key__buttons__save"
        depressed
        color="primary"
        :disabled="value === '' || loading"
        @click="save()"
      >
        Save
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import RevealableInput from '@/components/inputs/RevealableInput.vue';

@Component({
  components: {
    RevealableInput
  }
})
export default class ServiceKey extends Vue {
  @Prop({ required: true })
  value!: string;
  @Prop({ required: true })
  title!: string;
  @Prop({ required: false, default: false })
  loading!: boolean;
  @Prop({ required: false, default: '' })
  tooltip!: string;
  @Prop({ required: false, default: '' })
  hint!: string;
  @Prop({ required: false, default: '' })
  label!: string;

  @Emit()
  deleteKey() {}

  @Emit()
  save() {}

  @Emit()
  input(_value: string) {}
}
</script>

<style scoped lang="scss">
.service-key__content {
  flex-direction: row;
  display: flex;
  align-items: center;

  &__delete {
    max-width: 24px;
    margin-left: 16px;
  }
}
</style>
