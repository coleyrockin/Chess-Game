import { Chess, type Square } from 'chess.js';

import { isValidSquare, squareName } from './chessCoordinates';

export type PieceType = 'p' | 'n' | 'b' | 'r' | 'q' | 'k';
export type PieceColor = 'w' | 'b';
export type GameOutcome = 'white' | 'black' | 'draw' | null;

export type BoardPiece = {
  square: string;
  type: PieceType;
  color: PieceColor;
};

export type MatchScore = {
  whiteWins: number;
  blackWins: number;
  draws: number;
  gamesCompleted: number;
  gamesStarted: number;
};

export type ClickResult = {
  selectionChanged: boolean;
  boardChanged: boolean;
  moved: boolean;
  gameFinished: boolean;
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

  private selectedSquare: Square | null = null;

  private legalTargets = new Set<string>();

  private readonly match: MatchScore = {
    whiteWins: 0,
    blackWins: 0,
    draws: 0,
    gamesCompleted: 0,
    gamesStarted: 1,
  };

  private currentOutcome: GameOutcome = null;

  clickSquare(square: string): ClickResult {
    if (!isValidSquare(square)) {
      return { selectionChanged: false, boardChanged: false, moved: false, gameFinished: false };
    }

    if (this.isGameOver()) {
      return { selectionChanged: false, boardChanged: false, moved: false, gameFinished: true };
    }

    const boardSquare = square as Square;
    const clickedPiece = this.game.get(boardSquare);
    const turn = this.game.turn();

    if (!this.selectedSquare) {
      if (clickedPiece && clickedPiece.color === turn) {
        this.selectSquare(boardSquare);
        return { selectionChanged: true, boardChanged: false, moved: false, gameFinished: false };
      }
      return { selectionChanged: false, boardChanged: false, moved: false, gameFinished: false };
    }

    if (clickedPiece && clickedPiece.color === turn) {
      this.selectSquare(boardSquare);
      return { selectionChanged: true, boardChanged: false, moved: false, gameFinished: false };
    }

    if (!this.legalTargets.has(square)) {
      this.clearSelection();
      return { selectionChanged: true, boardChanged: false, moved: false, gameFinished: false };
    }

    const fromSquare = this.selectedSquare;
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
      return { selectionChanged: true, boardChanged: false, moved: false, gameFinished: false };
    }

    const gameFinished = this.captureOutcomeIfFinished();
    return { selectionChanged: true, boardChanged: true, moved: true, gameFinished };
  }

  resetBoard(): void {
    this.game.reset();
    this.currentOutcome = null;
    this.clearSelection();
  }

  newGame(): void {
    this.match.gamesStarted += 1;
    this.resetBoard();
  }

  statusText(): string {
    if (this.game.isCheckmate()) {
      return this.game.turn() === 'w' ? 'Checkmate | Black wins' : 'Checkmate | White wins';
    }
    if (this.game.isStalemate()) {
      return 'Stalemate | Draw';
    }
    if (this.game.isDraw()) {
      return 'Draw';
    }
    const turn = this.turnLabel();
    return this.game.isCheck() ? `${turn} to move (Check)` : `${turn} to move`;
  }

  scoreText(): string {
    const material = this.material();
    const diff = material.white - material.black;
    const evalText = diff === 0 ? 'Even' : diff > 0 ? `White +${diff}` : `Black +${Math.abs(diff)}`;
    return `Material W:${material.white} B:${material.black} | ${evalText}`;
  }

  matchText(): string {
    return `Match W:${this.match.whiteWins} B:${this.match.blackWins} D:${this.match.draws}`;
  }

  gameCounterText(): string {
    return `Game ${this.match.gamesStarted}`;
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

  selected(): Square | null {
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

  turnLabel(): 'White' | 'Black' {
    return this.turn() === 'w' ? 'White' : 'Black';
  }

  isGameOver(): boolean {
    return this.game.isGameOver();
  }

  outcome(): GameOutcome {
    return this.currentOutcome;
  }

  history(): string[] {
    return this.game.history();
  }

  fen(): string {
    return this.game.fen();
  }

  matchScore(): MatchScore {
    return { ...this.match };
  }

  private material(): { white: number; black: number } {
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

    return { white, black };
  }

  private captureOutcomeIfFinished(): boolean {
    if (!this.game.isGameOver()) {
      this.currentOutcome = null;
      return false;
    }

    if (this.game.isCheckmate()) {
      const winner: GameOutcome = this.game.turn() === 'w' ? 'black' : 'white';
      this.currentOutcome = winner;
      if (winner === 'white') {
        this.match.whiteWins += 1;
      } else {
        this.match.blackWins += 1;
      }
      this.match.gamesCompleted += 1;
      return true;
    }

    this.currentOutcome = 'draw';
    this.match.draws += 1;
    this.match.gamesCompleted += 1;
    return true;
  }

  private selectSquare(square: Square): void {
    this.selectedSquare = square;
    this.legalTargets = this.legalTargetsFrom(square);
  }

  private legalTargetsFrom(square: Square): Set<string> {
    const targets = new Set<string>();
    for (const move of this.game.moves({ square, verbose: true })) {
      targets.add(move.to);
    }
    return targets;
  }

  private clearSelection(): void {
    this.selectedSquare = null;
    this.legalTargets.clear();
  }
}
