export function randomHex(characters: number = 40): string {
  let hex: string = '';
  for (let i = 0; i < characters - 2; i++) {
    const randByte = parseInt((Math.random() * 16).toString(), 10).toString(16);
    hex += randByte;
  }
  return `0x${hex}ff`;
}
