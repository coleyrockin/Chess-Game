export function fileFromIndex(file: number): string {
  return String.fromCharCode('a'.charCodeAt(0) + file);
}

export function rankFromIndex(rank: number): string {
  return `${rank + 1}`;
}

export function squareName(file: number, rank: number): string {
  return `${fileFromIndex(file)}${rankFromIndex(rank)}`;
}

export function squareToIndices(square: string): { file: number; rank: number } {
  return {
    file: square.charCodeAt(0) - 'a'.charCodeAt(0),
    rank: Number.parseInt(square[1], 10) - 1,
  };
}
