import { defineComponent, h } from 'vue';

/**
 * Renders every slot `i18n-t` was given, default and named alike.
 *
 * @remarks
 * The shared setup stubs `I18nT` with `true`, which renders none of its slots, so anything
 * interactive inside a translated message is unreachable. Pass this through `global.stubs` to reach
 * it. Slots are rendered without being named, so a message whose slots change needs no edit here.
 */
export const I18nTStub = defineComponent({
  name: 'I18nT',
  setup(_props, { slots }) {
    return (): ReturnType<typeof h> => h('span', Object.values(slots).map(slot => slot?.()));
  },
});
