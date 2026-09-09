import { describe, expect, it } from 'vitest';
import { truncateToWidth } from '@/modules/shell/components/display/truncate-to-width';

/** Wide enough for `characters` glyphs at the label font's 7.21px per character. */
function widthFor(characters: number): number {
  return characters * 7.21;
}

const address = '0x9531C059098e3d194fF87FebB587aB07B30B1306';

describe('truncateToWidth', () => {
  it('should leave a label that fits alone', () => {
    expect(truncateToWidth(address, widthFor(address.length))).toBe(address);
  });

  it('should leave a label alone when there is room to spare', () => {
    expect(truncateToWidth('vault', widthFor(40))).toBe('vault');
  });

  it('should truncate a label that does not fit', () => {
    const truncated = truncateToWidth(address, widthFor(20));

    expect(truncated).not.toBe(address);
    expect(truncated).toContain('...');
  });

  /** The prefix is what makes an address recognisable, so it is kept rather than split through. */
  it('should keep the address prefix whole', () => {
    expect(truncateToWidth(address, widthFor(20)).startsWith('0x')).toBe(true);
  });

  it('should keep an xpub prefix whole', () => {
    const xpub = 'xpub68V4ZQSmhTHUAAmVPzDwSQpTX8FZLrNMFbfj9uMFyEsvvo1qC1x3W8Xy4mM8j2B';

    expect(truncateToWidth(xpub, widthFor(24)).startsWith('xpub')).toBe(true);
  });

  it('should keep the end of the label, which is what distinguishes two similar ones', () => {
    expect(truncateToWidth(address, widthFor(20)).endsWith('1306')).toBe(true);
  });

  it('should give a wider space more of the label', () => {
    const narrow = truncateToWidth(address, widthFor(16));
    const wide = truncateToWidth(address, widthFor(28));

    expect(wide.length).toBeGreaterThan(narrow.length);
  });

  /**
   * Zero is what an element reports before it has been measured. There is no budget to truncate
   * against, and the container hides the overflow, so the label is left for CSS to clip.
   */
  it('should leave the label alone while the space is unmeasured', () => {
    expect(truncateToWidth(address, 0)).toBe(address);
  });

  it('should leave a short label alone while unmeasured', () => {
    expect(truncateToWidth('bank', 0)).toBe('bank');
  });

  /** Truncating on a budget this small asks for a negative length and grows the label instead. */
  it('should never return more than it was given', () => {
    for (const width of [0, 1, 10, 20, 30, 40, 50]) {
      expect(truncateToWidth(address, width).length).toBeLessThanOrEqual(address.length);
    }
  });
});
