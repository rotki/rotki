import { describe, expect, it } from 'vitest';
import { getNonRootAttrs, getRootAttrs } from './attrs';

describe('getRootAttrs', () => {
  it('should pick class and all data-* attributes by default', () => {
    const attrs = { 'class': 'my-class', 'data-testid': 'foo', 'data-id': '1', 'onClick': (): void => {} };
    expect(getRootAttrs(attrs)).toEqual({ 'class': 'my-class', 'data-testid': 'foo', 'data-id': '1' });
  });

  it('should honour a custom include list', () => {
    const attrs = { 'id': 'root', 'class': 'x', 'data-testid': 'foo' };
    expect(getRootAttrs(attrs, ['id'])).toEqual({ 'id': 'root', 'data-testid': 'foo' });
  });

  it('should return only data-* attributes when nothing else matches', () => {
    const attrs = { 'data-a': '1', 'onClick': (): void => {} };
    expect(getRootAttrs(attrs, [])).toEqual({ 'data-a': '1' });
  });
});

describe('getNonRootAttrs', () => {
  it('should omit class and all data-* attributes by default', () => {
    const onClick = (): void => {};
    const attrs = { 'class': 'my-class', 'data-testid': 'foo', onClick };
    expect(getNonRootAttrs(attrs)).toEqual({ onClick });
  });

  it('should honour a custom exclude list', () => {
    const onClick = (): void => {};
    const attrs = { 'id': 'root', 'class': 'x', 'data-testid': 'foo', onClick };
    expect(getNonRootAttrs(attrs, ['id'])).toEqual({ class: 'x', onClick });
  });

  it('should be the complement of getRootAttrs', () => {
    const attrs = { 'class': 'x', 'data-a': '1', 'title': 'hello' };
    expect(getNonRootAttrs(attrs)).toEqual({ title: 'hello' });
    expect(getRootAttrs(attrs)).toEqual({ 'class': 'x', 'data-a': '1' });
  });
});
