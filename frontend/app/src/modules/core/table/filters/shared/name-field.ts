import type { FieldText } from '@/modules/core/table/pill/core/text';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

/**
 * The name pill, shared by every table that filters on something the user wrote.
 *
 * A name is typed rather than picked: there is no list of every custom asset name, address book
 * entry or balance label to offer, and the backend treats what is given as a substring. It is
 * single-valued for the same reason the backend is - one substring narrows, a second one would have
 * to mean either/or, which no endpoint here accepts.
 *
 * The label stays with the table: the same field is "name" in one and "label" in another, and that
 * is what the column beside it says.
 */
export function toNameField(key: string, label: FieldText): FieldDef {
  return toMatchFieldDef({
    freeText: true,
    key,
    label,
    multiple: false,
  });
}
