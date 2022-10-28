<template>
  <v-form ref="form" v-model="valid">
    <v-row>
      <tag-icon class="tag-creator__preview" :tag="tag" />
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-btn
            icon
            text
            class="tag-creator__random"
            v-on="on"
            @click="randomize"
          >
            <v-icon color="primary">mdi-refresh</v-icon>
          </v-btn>
        </template>
        <span>
          {{ t('tag_creator.refresh_tooltip') }}
        </span>
      </v-tooltip>
    </v-row>
    <v-row no-gutters align="center" class="mt-4">
      <v-col cols="12">
        <v-row no-gutters>
          <v-col cols="12">
            <v-text-field
              outlined
              class="tag_creator__name"
              :label="t('common.name')"
              :rules="rules"
              :value="tag.name"
              :disabled="editMode"
              @input="changed({ name: $event })"
            />
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12">
            <v-text-field
              outlined
              class="tag_creator__description"
              :value="tag.description"
              :label="t('tag_creator.labels.description')"
              @input="changed({ description: $event })"
            />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <v-row align="center" justify="center" no-gutters>
      <v-col md="6">
        <div class="mb-3 text-h6 text-center">
          {{ t('tag_creator.labels.foreground') }}
        </div>
        <v-row no-gutters>
          <v-col cols="12" class="tag-creator__color-picker">
            <v-color-picker
              flat
              class="tag-creator__color-picker__foreground"
              mode="hexa"
              hide-mode-switch
              :value="`#${tag.foregroundColor}`"
              @update:color="
                changed({ foregroundColor: $event.hex.replace('#', '') })
              "
            />
          </v-col>
        </v-row>
      </v-col>
      <v-col md="6">
        <div class="mb-3 text-h6 text-center">
          {{ t('tag_creator.labels.background') }}
        </div>
        <v-row no-gutters>
          <v-col cols="12" class="tag-creator__color-picker">
            <v-color-picker
              class="tag-creator__color-picker__background"
              flat
              hide-mode-switch
              mode="hexa"
              :value="`#${tag.backgroundColor}`"
              @update:color="
                changed({ backgroundColor: $event.hex.replace('#', '') })
              "
            />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <v-row class="mb-2">
      <v-col cols="12" class="d-flex justify-end">
        <v-btn
          v-if="editMode"
          class="mr-4"
          width="100"
          depressed
          @click="cancel"
        >
          {{ t('common.actions.cancel') }}
        </v-btn>
        <v-btn
          class="tag-creator__buttons__save"
          width="100"
          depressed
          color="primary"
          :disabled="!valid"
          @click="save"
        >
          {{ t('common.actions.save') }}
        </v-btn>
      </v-col>
    </v-row>
  </v-form>
</template>

<script setup lang="ts">
import { PropType, Ref } from 'vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { TagEvent } from '@/types/tags';
import { Tag } from '@/types/user';
import { invertColor, randomColor } from '@/utils/Color';

const props = defineProps({
  tag: { required: true, type: Object as PropType<Tag> },
  editMode: { required: true, type: Boolean }
});

const emit = defineEmits(['changed', 'save', 'cancel']);
const { t } = useI18n();

const { tag } = toRefs(props);
const valid = ref<boolean>(false);

const form: Ref<any> = ref(null);
const rules = [
  (v: string) => !!v || t('tag_creator.validation.empty_name').toString()
];

const changed = (event: TagEvent) => {
  emit('changed', {
    ...get(tag),
    ...event
  });
};

const save = () => {
  get(form)?.reset();
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
