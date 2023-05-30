describe('utils/text', () => {
  test('check return value of human readable function', () => {
    expect(toHumanReadable('lorem_ipsum dolor sit_amet')).toEqual(
      'lorem ipsum dolor sit amet'
    );
    expect(toHumanReadable('polygon_pos')).toEqual('polygon pos');
    expect(toHumanReadable('polygon_pos', 'uppercase')).toEqual('POLYGON POS');
    expect(toHumanReadable('polygon_pos', 'capitalize')).toEqual('Polygon Pos');
    expect(toHumanReadable('polygon_POS', 'capitalize')).toEqual('Polygon POS');
    expect(toHumanReadable('polygon_pos', 'sentence')).toEqual('Polygon pos');
    expect(toHumanReadable('POLYGON_POS', 'sentence')).toEqual('POLYGON POS');
    expect(toHumanReadable('polygon_pos', 'lowercase')).toEqual('polygon pos');
    expect(toHumanReadable('POLYGON_POS', 'lowercase')).toEqual('polygon pos');
    expect(toHumanReadable('POLYGON_pos', 'lowercase')).toEqual('polygon pos');
  });
});
