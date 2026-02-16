export const BOARD_FILES = 8;
export const BOARD_RANKS = 8;
const FILE_A_CODE = 'a'.charCodeAt(0);
const RANK_1_CODE = '1'.charCodeAt(0);

export type BoardSquare = `${'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h'}${'1' | '2' | '3' | '4' | '5' | '6' | '7' | '8'}`;

export function fileFromIndex(file: number): string {
  if (file < 0 || file >= BOARD_FILES || !Number.isInteger(file)) {
    throw new RangeError(`File index out of bounds: ${file}`);
  }
  return String.fromCharCode(FILE_A_CODE + file);
}

export function rankFromIndex(rank: number): string {
  if (rank < 0 || rank >= BOARD_RANKS || !Number.isInteger(rank)) {
    throw new RangeError(`Rank index out of bounds: ${rank}`);
  }
  return `${rank + 1}`;
}

export function squareName(file: number, rank: number): string {
  return `${fileFromIndex(file)}${rankFromIndex(rank)}`;
}

export function isSquareInBounds(file: number, rank: number): boolean {
  return file >= 0 && file < BOARD_FILES && rank >= 0 && rank < BOARD_RANKS;
}

export function isValidSquare(square: string): square is BoardSquare {
  if (square.length !== 2) {
    return false;
  }
  const fileCode = square.charCodeAt(0);
  const rankCode = square.charCodeAt(1);
  return fileCode >= FILE_A_CODE && fileCode < FILE_A_CODE + BOARD_FILES && rankCode >= RANK_1_CODE && rankCode < RANK_1_CODE + BOARD_RANKS;
}

export function squareToIndices(square: string): { file: number; rank: number } {
  if (!isValidSquare(square)) {
    throw new RangeError(`Invalid square: ${square}`);
  }
  return {
    file: square.charCodeAt(0) - FILE_A_CODE,
    rank: square.charCodeAt(1) - RANK_1_CODE,
  };
}
