import { Chess, type Square } from 'chess.js';

import { squareName } from './chessCoordinates';

export type PieceType = 'p' | 'n' | 'b' | 'r' | 'q' | 'k';
export type PieceColor = 'w' | 'b';

export type BoardPiece = {
  square: string;
  type: PieceType;
  color: PieceColor;
};

export type ClickResult = {
  selectionChanged: boolean;
  boardChanged: boolean;
  moved: boolean;
};

const PIECE_VALUE: Record<PieceType, number> = {
  p: 1,
  n: 3,
  b: 3,
  r: 5,
  q: 9,
  k: 0,
};

const PROMOTION_RANK_BY_COLOR: Record<PieceColor, string> = {
  w: '8',
  b: '1',
};

export class ChessGameController {
  private readonly game = new Chess();

  private selectedSquare: string | null = null;

  private legalTargets = new Set<string>();

  clickSquare(square: string): ClickResult {
    const boardSquare = square as Square;
    const clickedPiece = this.game.get(boardSquare);
    const turn = this.game.turn();

    if (!this.selectedSquare) {
      if (clickedPiece && clickedPiece.color === turn) {
        this.selectSquare(square);
        return { selectionChanged: true, boardChanged: false, moved: false };
      }
      return { selectionChanged: false, boardChanged: false, moved: false };
    }

    if (clickedPiece && clickedPiece.color === turn) {
      this.selectSquare(square);
      return { selectionChanged: true, boardChanged: false, moved: false };
    }

    if (!this.legalTargets.has(square)) {
      this.clearSelection();
      return { selectionChanged: true, boardChanged: false, moved: false };
    }

    const fromSquare = this.selectedSquare as Square;
    const movingPiece = this.game.get(fromSquare);
    const needsPromotion =
      movingPiece?.type === 'p' &&
      square[1] === PROMOTION_RANK_BY_COLOR[movingPiece.color as PieceColor];

    const move = this.game.move({
      from: fromSquare,
      to: boardSquare,
      ...(needsPromotion ? { promotion: 'q' } : {}),
    });

    this.clearSelection();

    if (!move) {
      return { selectionChanged: true, boardChanged: false, moved: false };
    }

    return { selectionChanged: true, boardChanged: true, moved: true };
  }

  reset(): void {
    this.game.reset();
    this.clearSelection();
  }

  statusText(): string {
    if (this.game.isCheckmate()) {
      return this.game.turn() === 'w' ? 'Checkmate | Black wins' : 'Checkmate | White wins';
    }
    if (this.game.isStalemate()) {
      return 'Stalemate';
    }
    if (this.game.isDraw()) {
      return 'Draw';
    }
    const turn = this.game.turn() === 'w' ? 'White' : 'Black';
    return this.game.isCheck() ? `${turn} to move (Check)` : `${turn} to move`;
  }

  scoreText(): string {
    let white = 0;
    let black = 0;

    for (const piece of this.pieces()) {
      const value = PIECE_VALUE[piece.type] ?? 0;
      if (piece.color === 'w') {
        white += value;
      } else {
        black += value;
      }
    }

    const diff = white - black;
    const evalText = diff === 0 ? 'Even' : diff > 0 ? `White +${diff}` : `Black +${Math.abs(diff)}`;
    return `Mat W:${white} B:${black} | ${evalText}`;
  }

  pieces(): BoardPiece[] {
    const result: BoardPiece[] = [];
    const rows = this.game.board();

    for (let rank = 0; rank < rows.length; rank += 1) {
      const row = rows[rank];
      for (let file = 0; file < row.length; file += 1) {
        const piece = row[file];
        if (!piece) {
          continue;
        }

        result.push({
          square: squareName(file, 7 - rank),
          type: piece.type as PieceType,
          color: piece.color as PieceColor,
        });
      }
    }

    return result;
  }

  selected(): string | null {
    return this.selectedSquare;
  }

  targets(): ReadonlySet<string> {
    return this.legalTargets;
  }

  targetsSorted(): string[] {
    return Array.from(this.legalTargets).sort();
  }

  turn(): PieceColor {
    return this.game.turn() as PieceColor;
  }

  fen(): string {
    return this.game.fen();
  }

  history(): string[] {
    return this.game.history();
  }

  private selectSquare(square: string): void {
    this.selectedSquare = square;
    this.legalTargets = this.legalTargetsFrom(square);
  }

  private legalTargetsFrom(square: string): Set<string> {
    const fromSquare = square as Square;
    const targets = new Set<string>();
    for (const move of this.game.moves({ square: fromSquare, verbose: true })) {
      targets.add(move.to);
    }
    return targets;
  }

  private clearSelection(): void {
    this.selectedSquare = null;
    this.legalTargets.clear();
  }
}
