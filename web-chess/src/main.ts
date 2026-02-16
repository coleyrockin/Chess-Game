import { AbstractEngine } from '@babylonjs/core/Engines/abstractEngine';
import { Engine } from '@babylonjs/core/Engines/engine';
import { WebGPUEngine } from '@babylonjs/core/Engines/webgpuEngine';

import { BoardScene, PIECE_BASE_Y, pieceHeight, squareToWorld } from './boardScene';
import { BOARD_FILES, BOARD_RANKS, squareName, squareToIndices } from './chessCoordinates';
import { ChessGameController, type BoardPiece, type PieceColor } from './chessGameController';

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
  debug_click_square?: (square: string) => void;
  debug_reset_game?: () => void;
  debug_new_game?: () => void;
  debug_flip_camera?: () => void;
  debug_set_renderer?: (mode: '2d' | '3d') => Promise<boolean>;
};

const appShell = requireElement<HTMLElement>('#app-shell');
const renderCanvas = requireElement<HTMLCanvasElement>('#game-canvas');
const fallbackCanvas = requireElement<HTMLCanvasElement>('#fallback-canvas');
const gameCounterText = requireElement<HTMLParagraphElement>('#game-counter');
const statusText = requireElement<HTMLParagraphElement>('#status');
const turnText = requireElement<HTMLParagraphElement>('#turn-indicator');
const lastMoveText = requireElement<HTMLParagraphElement>('#last-move');
const materialText = requireElement<HTMLParagraphElement>('#material-score');
const matchText = requireElement<HTMLParagraphElement>('#match-score');
const newGameButton = requireElement<HTMLButtonElement>('#new-game-btn');
const resetButton = requireElement<HTMLButtonElement>('#reset-board-btn');
const flipCameraButton = requireElement<HTMLButtonElement>('#flip-camera-btn');
const rendererModeButton = requireElement<HTMLButtonElement>('#renderer-mode-btn');

const game = new ChessGameController();

let engine: AbstractEngine | null = null;
let boardScene: BoardScene | null = null;
let fallbackRenderer: Canvas2DChessFallback | null = null;
let fallbackFrameId: number | null = null;
let engineLoopActive = false;
let engineFrameLast = 0;
let viewPerspective: PieceColor = 'w';
let rendererMode: '2d' | '3d' = '2d';

class Canvas2DChessFallback {
  private readonly ctx: CanvasRenderingContext2D;

  private boardX = 0;

  private boardY = 0;

  private boardSize = 0;

  private tileSize = 0;

  private elapsed = 0;

  constructor(
    private readonly targetCanvas: HTMLCanvasElement,
    private readonly onSquareClick: (square: string) => void,
  ) {
    const ctx = this.targetCanvas.getContext('2d');
    if (!ctx) {
      throw new Error('2D canvas context not available.');
    }
    this.ctx = ctx;
    this.targetCanvas.addEventListener('click', this.handleClick);
    this.resize();
  }

  destroy(): void {
    this.targetCanvas.removeEventListener('click', this.handleClick);
  }

  resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.floor(this.targetCanvas.clientWidth * dpr));
    const height = Math.max(1, Math.floor(this.targetCanvas.clientHeight * dpr));
    if (this.targetCanvas.width !== width || this.targetCanvas.height !== height) {
      this.targetCanvas.width = width;
      this.targetCanvas.height = height;
    }

    this.boardSize = Math.min(width, height) * 0.8;
    this.tileSize = this.boardSize / 8;
    this.boardX = (width - this.boardSize) * 0.5;
    this.boardY = (height - this.boardSize) * 0.5;
  }

  update(dt: number): void {
    this.elapsed += dt;
  }

  render(
    selectedSquare: string | null,
    legalTargets: ReadonlySet<string>,
    pieces: readonly BoardPiece[],
    turn: PieceColor,
    perspective: PieceColor,
  ): void {
    const { ctx } = this;
    const width = this.targetCanvas.width;
    const height = this.targetCanvas.height;

    const bg = ctx.createRadialGradient(width * 0.5, height * 0.25, width * 0.12, width * 0.5, height * 0.7, width);
    bg.addColorStop(0, '#13254a');
    bg.addColorStop(1, '#020714');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = '#0b1a37';
    ctx.fillRect(
      this.boardX - this.tileSize * 0.35,
      this.boardY - this.tileSize * 0.35,
      this.boardSize + this.tileSize * 0.7,
      this.boardSize + this.tileSize * 0.7,
    );

    const pulse = (Math.sin(this.elapsed * 5) + 1) * 0.5;
    for (let row = 0; row < BOARD_RANKS; row += 1) {
      for (let col = 0; col < BOARD_FILES; col += 1) {
        const file = perspective === 'w' ? col : (BOARD_FILES - 1 - col);
        const rank = perspective === 'w' ? (BOARD_RANKS - 1 - row) : row;
        const square = squareName(file, rank);
        const x = this.boardX + (col * this.tileSize);
        const y = this.boardY + (row * this.tileSize);
        const isLight = (file + rank) % 2 === 0;
        let fill = isLight ? '#95a9d0' : '#20345a';
        if (legalTargets.has(square)) {
          fill = pulse > 0.5 ? '#67be57' : '#519e44';
        }
        if (selectedSquare === square) {
          fill = pulse > 0.5 ? '#e58d35' : '#c96f22';
        }
        ctx.fillStyle = fill;
        ctx.fillRect(x, y, this.tileSize, this.tileSize);
      }
    }

    for (const piece of pieces) {
      const center = this.squareCenter(piece.square, perspective);
      const accent = accentByType(piece.type);
      const radius = this.tileSize * 0.33;

      ctx.beginPath();
      ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = piece.color === 'w' ? '#eef5ff' : '#0d1626';
      ctx.fill();
      ctx.lineWidth = Math.max(2, this.tileSize * 0.05);
      ctx.strokeStyle = accent;
      ctx.stroke();

      ctx.fillStyle = piece.color === 'w' ? '#142743' : '#dce9ff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = `${Math.floor(this.tileSize * 0.4)}px Rajdhani, sans-serif`;
      ctx.fillText(piece.type.toUpperCase(), center.x, center.y + this.tileSize * 0.01);
    }

    ctx.fillStyle = 'rgba(7, 15, 31, 0.85)';
    ctx.fillRect(this.boardX, this.boardY - this.tileSize * 0.42, this.tileSize * 3.85, this.tileSize * 0.28);
    ctx.fillStyle = '#dceaff';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.font = `${Math.floor(this.tileSize * 0.19)}px Rajdhani, sans-serif`;
    ctx.fillText(
      `Safe 2D | ${turn === 'w' ? 'White' : 'Black'} to move | View ${perspective === 'w' ? 'White' : 'Black'}`,
      this.boardX + this.tileSize * 0.12,
      this.boardY - this.tileSize * 0.28,
    );
  }

  private readonly handleClick = (event: MouseEvent): void => {
    const rect = this.targetCanvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * (this.targetCanvas.width / rect.width);
    const y = (event.clientY - rect.top) * (this.targetCanvas.height / rect.height);
    const square = this.squareFromCanvasPoint(x, y, viewPerspective);
    if (square) {
      this.onSquareClick(square);
    }
  };

  private squareFromCanvasPoint(x: number, y: number, perspective: PieceColor): string | null {
    if (x < this.boardX || y < this.boardY || x >= this.boardX + this.boardSize || y >= this.boardY + this.boardSize) {
      return null;
    }

    const col = Math.floor((x - this.boardX) / this.tileSize);
    const row = Math.floor((y - this.boardY) / this.tileSize);
    if (col < 0 || col > 7 || row < 0 || row > 7) {
      return null;
    }

    const file = perspective === 'w' ? col : (BOARD_FILES - 1 - col);
    const rank = perspective === 'w' ? (BOARD_RANKS - 1 - row) : row;
    return squareName(file, rank);
  }

  private squareCenter(square: string, perspective: PieceColor): { x: number; y: number } {
    let file: number;
    let rank: number;
    try {
      ({ file, rank } = squareToIndices(square));
    } catch {
      return {
        x: this.boardX + (this.boardSize * 0.5),
        y: this.boardY + (this.boardSize * 0.5),
      };
    }
    const col = perspective === 'w' ? file : (BOARD_FILES - 1 - file);
    const row = perspective === 'w' ? (BOARD_RANKS - 1 - rank) : rank;
    return {
      x: this.boardX + ((col + 0.5) * this.tileSize),
      y: this.boardY + ((row + 0.5) * this.tileSize),
    };
  }
}

function accentByType(type: BoardPiece['type']): string {
  switch (type) {
    case 'p':
      return '#39bff0';
    case 'n':
      return '#ff9342';
    case 'b':
      return '#56de72';
    case 'r':
      return '#f3d246';
    case 'q':
      return '#d683ff';
    case 'k':
      return '#ff6f6f';
    default:
      return '#b0c6ef';
  }
}

async function tryWebGpuEngine(target: HTMLCanvasElement): Promise<AbstractEngine | null> {
  const nav = navigator as Navigator & { gpu?: unknown };
  const isHeadless = /HeadlessChrome/i.test(navigator.userAgent);
  if (!nav.gpu || isHeadless) {
    return null;
  }

  try {
    const webgpu = new WebGPUEngine(target, {
      antialias: true,
      adaptToDeviceRatio: true,
    });
    await Promise.race([
      webgpu.initAsync(),
      new Promise<never>((_, reject) => {
        window.setTimeout(() => reject(new Error('WebGPU init timeout')), 2200);
      }),
    ]);
    return webgpu;
  } catch (error) {
    console.warn('WebGPU init failed, falling back to WebGL.', error);
    return null;
  }
}

function tryWebGlEngine(
  target: HTMLCanvasElement,
  options: ConstructorParameters<typeof Engine>[2],
): AbstractEngine | null {
  try {
    return new Engine(target, true, options);
  } catch (error) {
    console.warn('WebGL engine init attempt failed.', error);
    return null;
  }
}

async function createEngine(target: HTMLCanvasElement): Promise<AbstractEngine> {
  const webgpu = await tryWebGpuEngine(target);
  if (webgpu) {
    return webgpu;
  }

  const webgl2 = tryWebGlEngine(target, {
    preserveDrawingBuffer: true,
    stencil: true,
  });
  if (webgl2) {
    return webgl2;
  }

  const webgl1 = tryWebGlEngine(target, {
    preserveDrawingBuffer: true,
    stencil: false,
    disableWebGL2Support: true,
  });
  if (webgl1) {
    return webgl1;
  }

  throw new Error('Unable to initialize WebGPU/WebGL on this browser/device.');
}

function setCanvasVisibility(mode: '2d' | '3d'): void {
  if (mode === '3d') {
    renderCanvas.style.visibility = 'visible';
    renderCanvas.style.pointerEvents = 'auto';
    fallbackCanvas.style.visibility = 'hidden';
    fallbackCanvas.style.pointerEvents = 'none';
  } else {
    renderCanvas.style.visibility = 'hidden';
    renderCanvas.style.pointerEvents = 'none';
    fallbackCanvas.style.visibility = 'visible';
    fallbackCanvas.style.pointerEvents = 'auto';
  }
}

function updateHud(): void {
  const history = game.history();
  const lastMove = history.length > 0 ? history[history.length - 1] : null;
  const mover = game.turn() === 'w' ? 'Black' : 'White';

  gameCounterText.textContent = game.gameCounterText();
  statusText.textContent = game.statusText();
  turnText.textContent =
    `Turn: ${game.turnLabel()} | Camera: ${viewPerspective === 'w' ? 'White Side' : 'Black Side'} | Renderer: ${rendererMode.toUpperCase()}`;
  lastMoveText.textContent = lastMove ? `Last move: ${mover} ${lastMove}` : 'Last move: --';
  materialText.textContent = game.scoreText();
  matchText.textContent = game.matchText();
  rendererModeButton.textContent = rendererMode === '3d' ? 'Switch Renderer (M) -> 2D Safe' : 'Switch Renderer (M) -> 3D';

  if (game.isGameOver()) {
    const outcome = game.outcome();
    if (outcome === 'white') {
      statusText.textContent = 'Game Over | White wins. Start a new game.';
    } else if (outcome === 'black') {
      statusText.textContent = 'Game Over | Black wins. Start a new game.';
    } else {
      statusText.textContent = 'Game Over | Draw. Start a new game.';
    }
  }
}

function syncBoardVisuals(): void {
  if (!boardScene) {
    return;
  }
  boardScene.syncPieces(game.pieces());
  boardScene.setTurn(game.turn());
  boardScene.setPerspective(viewPerspective);
}

function renderFrame(): void {
  if (rendererMode === '3d') {
    boardScene?.render();
    return;
  }
  fallbackRenderer?.render(game.selected(), game.targets(), game.pieces(), game.turn(), viewPerspective);
}

function handleSquareClick(square: string): void {
  const click = game.clickSquare(square);
  if (click.boardChanged) {
    syncBoardVisuals();
  }
  if (click.selectionChanged || click.boardChanged || click.moved || click.gameFinished) {
    updateHud();
    renderFrame();
  }
}

function newGame(): void {
  game.newGame();
  syncBoardVisuals();
  updateHud();
  renderFrame();
}

function resetBoard(): void {
  game.resetBoard();
  syncBoardVisuals();
  updateHud();
  renderFrame();
}

function setPerspective(color: PieceColor): void {
  viewPerspective = color;
  boardScene?.setPerspective(viewPerspective);
  updateHud();
  renderFrame();
}

function togglePerspective(): void {
  setPerspective(viewPerspective === 'w' ? 'b' : 'w');
}

async function toggleFullscreen(target: HTMLElement): Promise<void> {
  if (document.fullscreenElement) {
    await document.exitFullscreen();
    return;
  }
  await target.requestFullscreen();
}

function startEngineLoop(): void {
  if (!engine || !boardScene || engineLoopActive) {
    return;
  }

  const scene = boardScene;
  engineFrameLast = performance.now();
  engine.runRenderLoop(() => {
    const now = performance.now();
    const dt = Math.min(0.05, (now - engineFrameLast) / 1000);
    engineFrameLast = now;
    if (rendererMode !== '3d') {
      return;
    }
    scene.update(dt, game.selected(), game.targets());
    scene.render();
  });
  engineLoopActive = true;
}

function stopEngineLoop(): void {
  if (!engine || !engineLoopActive) {
    return;
  }
  engine.stopRenderLoop();
  engineLoopActive = false;
}

function stopFallbackLoop(): void {
  if (fallbackFrameId !== null) {
    window.cancelAnimationFrame(fallbackFrameId);
    fallbackFrameId = null;
  }
}

function startFallbackLoop(): void {
  stopFallbackLoop();
  let last = performance.now();
  const frame = (now: number) => {
    if (rendererMode !== '2d' || !fallbackRenderer) {
      return;
    }
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    fallbackRenderer.update(dt);
    fallbackRenderer.render(game.selected(), game.targets(), game.pieces(), game.turn(), viewPerspective);
    fallbackFrameId = window.requestAnimationFrame(frame);
  };
  fallbackFrameId = window.requestAnimationFrame(frame);
}

function ensureFallbackRenderer(): void {
  if (!fallbackRenderer) {
    fallbackRenderer = new Canvas2DChessFallback(fallbackCanvas, handleSquareClick);
  }
}

function activateFallback(reason?: string): void {
  ensureFallbackRenderer();
  rendererMode = '2d';
  setCanvasVisibility('2d');
  stopEngineLoop();
  startFallbackLoop();
  updateHud();
  renderFrame();
  if (reason) {
    console.warn(`Using safe 2D renderer: ${reason}`);
  }
}

function activate3D(): boolean {
  if (!engine || !boardScene) {
    return false;
  }

  rendererMode = '3d';
  setCanvasVisibility('3d');
  stopFallbackLoop();
  fallbackRenderer?.destroy();
  fallbackRenderer = null;
  syncBoardVisuals();
  updateHud();
  startEngineLoop();
  renderFrame();
  return true;
}

async function ensure3DInitialized(): Promise<boolean> {
  if (engine && boardScene) {
    return true;
  }

  try {
    engine = await createEngine(renderCanvas);
    boardScene = new BoardScene(engine, handleSquareClick);
    boardScene.setPerspective(viewPerspective);
    syncBoardVisuals();
    return true;
  } catch (error) {
    console.warn('3D renderer unavailable. Staying in safe 2D mode.', error);
    engine = null;
    boardScene = null;
    return false;
  }
}

async function setRendererMode(mode: '2d' | '3d'): Promise<boolean> {
  if (mode === '2d') {
    activateFallback('manual switch');
    return true;
  }

  const ready = await ensure3DInitialized();
  if (!ready) {
    activateFallback('3D init failed');
    return false;
  }
  return activate3D();
}

async function toggleRendererMode(): Promise<void> {
  if (rendererMode === '3d') {
    await setRendererMode('2d');
    return;
  }
  await setRendererMode('3d');
}

function handleKeyDown(event: KeyboardEvent): void {
  const key = event.key.toLowerCase();

  if (key === 'r') {
    resetBoard();
    event.preventDefault();
    return;
  }

  if (key === 'n') {
    newGame();
    event.preventDefault();
    return;
  }

  if (key === 'v') {
    togglePerspective();
    event.preventDefault();
    return;
  }

  if (key === 'm') {
    void toggleRendererMode();
    event.preventDefault();
    return;
  }

  if (key === 'f') {
    void toggleFullscreen(appShell);
    event.preventDefault();
    return;
  }

  if (key === 'escape' && document.fullscreenElement) {
    void document.exitFullscreen();
  }
}

function onResize(): void {
  if (rendererMode === '3d') {
    boardScene?.resize();
  } else if (fallbackRenderer) {
    fallbackRenderer.resize();
    renderFrame();
  }
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
      click: 'select piece, then select legal destination square',
      r: 'reset current board',
      n: 'start next game',
      v: 'flip camera side',
      m: 'switch renderer (3D/2D safe)',
      f: 'toggle fullscreen',
      esc: 'exit fullscreen',
    },
    renderer_mode: rendererMode,
    turn: game.turn(),
    turn_label: game.turnLabel(),
    status: game.statusText(),
    material_score: game.scoreText(),
    match_score: game.matchScore(),
    match_text: game.matchText(),
    game_counter: game.gameCounterText(),
    perspective: viewPerspective,
    is_game_over: game.isGameOver(),
    outcome: game.outcome(),
    selected_square: game.selected(),
    legal_targets: game.targetsSorted(),
    fen: game.fen(),
    history: game.history(),
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
  const hooksWindow = window as TestHooksWindow;
  hooksWindow.render_game_to_text = textState;
  hooksWindow.advanceTime = async (ms: number) => {
    const steps = Math.max(1, Math.round(ms / (1000 / 60)));
    for (let i = 0; i < steps; i += 1) {
      const scene = boardScene;
      const fallback = fallbackRenderer;
      if (rendererMode === '3d' && scene) {
        scene.update(1 / 60, game.selected(), game.targets());
      } else if (rendererMode === '2d' && fallback) {
        fallback.update(1 / 60);
      }
    }
    renderFrame();
  };
  hooksWindow.debug_click_square = (square: string) => {
    handleSquareClick(square);
  };
  hooksWindow.debug_reset_game = () => {
    resetBoard();
  };
  hooksWindow.debug_new_game = () => {
    newGame();
  };
  hooksWindow.debug_flip_camera = () => {
    togglePerspective();
  };
  hooksWindow.debug_set_renderer = async (mode: '2d' | '3d') => setRendererMode(mode);

  window.addEventListener('resize', onResize);
  window.addEventListener('keydown', handleKeyDown);
  newGameButton.addEventListener('click', () => {
    newGame();
  });
  resetButton.addEventListener('click', () => {
    resetBoard();
  });
  flipCameraButton.addEventListener('click', () => {
    togglePerspective();
  });
  rendererModeButton.addEventListener('click', () => {
    void toggleRendererMode();
  });

  renderCanvas.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    activateFallback('WebGL context lost');
  });

  activateFallback('startup safe mode');
  const initialized3D = await ensure3DInitialized();
  if (initialized3D) {
    const switched = activate3D();
    if (!switched) {
      activateFallback('3D switch failed');
    }
  } else {
    activateFallback('3D not available');
  }
}

void start();
