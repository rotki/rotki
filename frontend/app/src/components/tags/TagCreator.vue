<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { type Ref } from 'vue';
import { type Tag, type TagEvent } from '@/types/tags';

const props = defineProps<{
  tag: Tag;
  editMode: boolean;
}>();

const emit = defineEmits(['changed', 'save', 'cancel']);
const { t } = useI18n();

const { tag } = toRefs(props);

const form: Ref = ref(null);

const rules = {
  name: {
    required: helpers.withMessage(
      t('tag_creator.validation.empty_name').toString(),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    name: computed(() => get(tag).name)
  },
  { $autoDirty: true }
);

const changed = (event: TagEvent) => {
  emit('changed', {
    ...get(tag),
    ...event
  });
};

const save = () => {
  get(form)?.reset();
  nextTick(() => {
    get(v$).$reset();
  });
  emit('save', get(tag));
};

const cancel = () => {
  get(form)?.reset();
  emit('cancel');
};

const randomize = () => {
  const backgroundColor = randomColor();
  changed({
    backgroundColor,
    foregroundColor: invertColor(backgroundColor)
  });
};
</script>

<template>
  <VForm ref="form" :value="!v$.$invalid">
    <VRow>
      <TagIcon class="tag-creator__preview" :tag="tag" />
      <VTooltip bottom>
        <template #activator="{ on }">
          <RuiButton
            icon
            variant="text"
            class="tag-creator__random"
            color="primary"
            v-on="on"
            @click="randomize()"
          >
            <RuiIcon name="shuffle-line" />
          </RuiButton>
        </template>
        <span>
          {{ t('tag_creator.refresh_tooltip') }}
        </span>
      </VTooltip>
    </VRow>
    <VRow no-gutters align="center" class="mt-4">
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12">
            <VTextField
              outlined
              class="tag_creator__name"
              :label="t('common.name')"
              :error-messages="v$.name.$errors.map(e => e.$message)"
              :value="tag.name"
              :disabled="editMode"
              @input="changed({ name: $event })"
            />
          </VCol>
        </VRow>
        <VRow no-gutters>
          <VCol cols="12">
            <VTextField
              outlined
              class="tag_creator__description"
              :value="tag.description"
              :label="t('common.description')"
              @input="changed({ description: $event })"
            />
          </VCol>
        </VRow>
      </VCol>
    </VRow>
    <VRow align="center" justify="center" no-gutters>
      <VCol md="6">
        <div class="mb-3 text-h6 text-center">
          {{ t('tag_creator.labels.foreground') }}
        </div>
        <VRow no-gutters>
          <VCol cols="12" class="tag-creator__color-picker">
            <VColorPicker
              flat
              class="tag-creator__color-picker__foreground"
              mode="hexa"
              hide-mode-switch
              :value="`#${tag.foregroundColor}`"
              @update:color="
                changed({ foregroundColor: $event.hex.replace('#', '') })
              "
            />
          </VCol>
        </VRow>
      </VCol>
      <VCol md="6">
        <div class="mb-3 text-h6 text-center">
          {{ t('tag_creator.labels.background') }}
        </div>
        <VRow no-gutters>
          <VCol cols="12" class="tag-creator__color-picker">
            <VColorPicker
              class="tag-creator__color-picker__background"
              flat
              hide-mode-switch
              mode="hexa"
              :value="`#${tag.backgroundColor}`"
              @update:color="
                changed({ backgroundColor: $event.hex.replace('#', '') })
              "
            />
          </VCol>
        </VRow>
      </VCol>
    </VRow>
    <VRow class="mb-2">
      <VCol cols="12" class="flex justify-end">
        <RuiButton v-if="editMode" class="mr-4" width="100" @click="cancel()">
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          class="tag-creator__buttons__save"
          width="100"
          color="primary"
          :disabled="v$.$invalid"
          @click="save()"
        >
          {{ t('common.actions.save') }}
        </RuiButton>
      </VCol>
    </VRow>
  </VForm>
</template>

<style scoped lang="scss">
.tag-creator {
  &__preview {
    min-width: 120px;
    margin-left: 12px;
    margin-bottom: 10px;
  }

  &__color-picker {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__random {
    margin-left: 16px;
  }

  &__buttons {
    &__save {
      margin-right: 8px;
    }
  }
}
</style>
