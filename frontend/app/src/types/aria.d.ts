export {};

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
