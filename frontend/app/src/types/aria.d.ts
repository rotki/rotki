import type { AriaAttributes } from 'vue';

declare module '@vue/runtime-dom' {
  /**
   * ARIA attributes Vue's DOM types do not list yet.
   *
   * @remarks
   * `aria-description` is ARIA 1.3: a description read out after the accessible name, for a hint
   * that has no element of its own to point `aria-describedby` at.
   */
  interface AriaAttributes {
    'aria-description'?: string;
  }
}

declare module 'vue' {
  /**
   * Lets any component take ARIA attributes, which fall through to its root element.
   *
   * @remarks
   * With `strictTemplates` an attribute a component does not declare is a type error. A third-party
   * component such as `VChart` declares none, yet labelling its root is the only way to name it.
   * `data-*` attributes get the same allowance through `dataAttributes` in `tsconfig.app.json`.
   */
  interface ComponentCustomProps extends AriaAttributes {}
}
