export function generateRandomScrambleMultiplier(): number {
  return Math.floor(500 + Math.random() * 9500) / 1000;
}
