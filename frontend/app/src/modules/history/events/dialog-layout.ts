/**
 * The height cap the history event dialogs give their scrolling content.
 *
 * @remarks
 * Subtracts the chrome these dialogs put above and below the scroll area, so the pager stays on
 * screen rather than being pushed past the bottom. Measured rather than derived, because none of
 * these hosts propagates a bounded flex height down to the scroll area.
 *
 * The pinned surfaces pass `undefined` instead: the sidebar already bounds them, and capping again
 * would leave them short.
 */
export const HISTORY_DIALOG_MAX_HEIGHT = 'calc(100vh - 23rem)';
