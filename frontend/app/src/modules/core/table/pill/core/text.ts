/**
 * A piece of a field's copy: the finished string, or a getter resolved where the bar draws it.
 *
 * A getter is what lets a field be built once and still track the locale. Everything else on a
 * `FieldDef` that depends on live data is already a function (`suggest`, `resolveLabel`, `admits`),
 * so eager copy was the only reason a table had to rebuild its whole field list inside a
 * `computed`. Resolution happens inside the components' own computeds, which is what registers the
 * locale dependency.
 */
export type FieldText = string | (() => string);

/** Resolves a field's copy at the point it is drawn. */
export function resolveText(text: FieldText): string {
  return typeof text === 'function' ? text() : text;
}

/** {@link resolveText} for copy a field may omit. */
export function resolveOptionalText(text?: FieldText): string | undefined {
  return text === undefined ? undefined : resolveText(text);
}
