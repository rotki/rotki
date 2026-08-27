/**
 * Keeps a swap form's fee rows in step with its has-fee toggle.
 *
 * @remarks
 * Turning the toggle off clears the rows. Turning it on adds one blank row, but *only* when there
 * are none: seeding an existing group sets the flag and the rows together, so replacing them
 * unconditionally would discard the fees that were just loaded.
 *
 * Every swap form needs this, and each holds its rows under a different name with a different row
 * shape, which is why both the rows and their factory are passed in.
 *
 * @param hasFee - reads the form's has-fee toggle
 * @param rows - reads the form's fee rows; edited in place, so the form keeps the same array
 * @param createRow - builds one blank row of this form's fee shape
 */
export function useFeeRows<T>(hasFee: () => boolean, rows: () => T[], createRow: () => T): void {
  watch(hasFee, (enabled) => {
    const current = rows();

    if (!enabled) {
      current.splice(0, current.length);
      return;
    }

    if (current.length === 0)
      current.push(createRow());
  });
}
