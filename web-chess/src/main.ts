import { AbstractEngine } from '@babylonjs/core/Engines/abstractEngine';
import { Engine } from '@babylonjs/core/Engines/engine';
import { WebGPUEngine } from '@babylonjs/core/Engines/webgpuEngine';

import { BoardScene, PIECE_BASE_Y, pieceHeight, squareToWorld } from './boardScene';
import { ChessGameController } from './chessGameController';

function requireElement<T extends HTMLElement>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) {
    throw new Error(`Missing required DOM element: ${selector}`);
  }
  return element;
}

type TestHooksWindow = Window & {
  render_game_to_text?: () => string;
  advanceTime?: (ms: number) => Promise<void>;
};

const canvas = requireElement<HTMLCanvasElement>('#game-canvas');
const statusText = requireElement<HTMLParagraphElement>('#status');
const lastMoveText = requireElement<HTMLParagraphElement>('#last-move');
const moveCountText = requireElement<HTMLParagraphElement>('#move-count');
const scoreText = requireElement<HTMLParagraphElement>('#score');

const game = new ChessGameController();

let engine: AbstractEngine;
let boardScene: BoardScene;

async function createEngine(target: HTMLCanvasElement): Promise<AbstractEngine> {
  const nav = navigator as Navigator & { gpu?: unknown };
  const isHeadless = /HeadlessChrome/i.test(navigator.userAgent);

  if (nav.gpu && !isHeadless) {
    try {
      const webgpu = new WebGPUEngine(target, {
        antialias: true,
        adaptToDeviceRatio: true,
      });
      await webgpu.initAsync();
      return webgpu;
    } catch (error) {
      console.warn('WebGPU init failed, falling back to WebGL2.', error);
    }
  }

  return new Engine(target, true, {
    preserveDrawingBuffer: true,
    stencil: true,
  });
}

function updateHud(): void {
  const history = game.history();
  const lastMove = history.length > 0 ? history[history.length - 1] : null;
  const movesPlayed = Math.ceil(history.length / 2);

  if (lastMove) {
    const lastSide = game.turn() === 'w' ? 'Black' : 'White';
    lastMoveText.textContent = `Last move: ${lastSide} ${lastMove}`;
  } else {
    lastMoveText.textContent = 'Last move: --';
  }

  moveCountText.textContent = `Moves played: ${movesPlayed}`;
  statusText.textContent = game.statusText();
  scoreText.textContent = game.scoreText();
}

function syncBoardVisuals(): void {
  boardScene.syncPieces(game.pieces());
  boardScene.setTurn(game.turn());
}

function handleSquareClick(square: string): void {
  const click = game.clickSquare(square);
  if (click.boardChanged) {
    syncBoardVisuals();
  }
  if (click.selectionChanged || click.boardChanged || click.moved) {
    updateHud();
  }
}

function resetGame(): void {
  game.reset();
  syncBoardVisuals();
  updateHud();
}

async function toggleFullscreen(target: HTMLElement): Promise<void> {
  if (document.fullscreenElement) {
    await document.exitFullscreen();
    return;
  }
  await target.requestFullscreen();
}

function handleKeyDown(event: KeyboardEvent): void {
  const key = event.key.toLowerCase();

  if (key === 'r') {
    resetGame();
    event.preventDefault();
    return;
  }

  if (key === 'f') {
    void toggleFullscreen(canvas);
    event.preventDefault();
    return;
  }

  if (key === 'escape' && document.fullscreenElement) {
    void document.exitFullscreen();
  }
}

function tick(dt: number): void {
  boardScene.update(dt, game.selected(), game.targets());
}

function textState(): string {
  const payload = {
    mode: 'playing',
    coordinate_system: {
      origin: 'board center',
      x_axis: 'files increase from a to h',
      z_axis: 'ranks increase from 1 to 8',
      y_axis: 'up',
    },
    controls: {
      click: 'select piece or legal destination square',
      r: 'reset board',
      f: 'toggle fullscreen',
      esc: 'exit fullscreen',
    },
    turn: game.turn(),
    status: game.statusText(),
    score: game.scoreText(),
    selected_square: game.selected(),
    legal_targets: game.targetsSorted(),
    fen: game.fen(),
    pieces: game.pieces().map((piece) => {
      const world = squareToWorld(piece.square);
      return {
        square: piece.square,
        type: piece.type,
        color: piece.color,
        x: Number(world.x.toFixed(3)),
        y: Number((PIECE_BASE_Y + (pieceHeight(piece.type) * 0.5)).toFixed(3)),
        z: Number(world.z.toFixed(3)),
      };
    }),
  };
  return JSON.stringify(payload);
}

async function start(): Promise<void> {
  engine = await createEngine(canvas);
  boardScene = new BoardScene(engine, handleSquareClick);

  syncBoardVisuals();
  updateHud();
  tick(0);

  let last = performance.now();
  engine.runRenderLoop(() => {
    const now = performance.now();
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;

    tick(dt);
    boardScene.render();
  });

  window.addEventListener('resize', () => {
    boardScene.resize();
  });
  window.addEventListener('keydown', handleKeyDown);

  const hooksWindow = window as TestHooksWindow;
  hooksWindow.render_game_to_text = textState;
  hooksWindow.advanceTime = async (ms: number) => {
    const steps = Math.max(1, Math.round(ms / (1000 / 60)));
    for (let i = 0; i < steps; i += 1) {
      tick(1 / 60);
    }
    boardScene.render();
  };
}

void start();
