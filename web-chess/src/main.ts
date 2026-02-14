import { AbstractMesh } from '@babylonjs/core/Meshes/abstractMesh';
import { ArcRotateCamera } from '@babylonjs/core/Cameras/arcRotateCamera';
import { Color3, Color4, Quaternion, Vector3 } from '@babylonjs/core/Maths/math';
import { Engine } from '@babylonjs/core/Engines/engine';
import { WebGPUEngine } from '@babylonjs/core/Engines/webgpuEngine';
import { GlowLayer } from '@babylonjs/core/Layers/glowLayer';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { Mesh } from '@babylonjs/core/Meshes/mesh';
import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import { PointerEventTypes } from '@babylonjs/core/Events/pointerEvents';
import { Scene } from '@babylonjs/core/scene';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { Chess } from 'chess.js';

const canvas = document.querySelector<HTMLCanvasElement>('#game-canvas');
const statusText = document.querySelector<HTMLParagraphElement>('#status');
const scoreText = document.querySelector<HTMLParagraphElement>('#score');

if (!canvas || !statusText || !scoreText) {
  throw new Error('Required DOM nodes are missing.');
}

const TILE_SIZE = 1.0;
const PIECE_BASE_Y = 0.35;

type PieceType = 'p' | 'n' | 'b' | 'r' | 'q' | 'k';
type PieceColor = 'w' | 'b';

type TileVisual = {
  mesh: Mesh;
  material: StandardMaterial;
  baseColor: Color3;
};

type PieceVisual = {
  mesh: Mesh;
  square: string;
  type: PieceType;
  color: PieceColor;
};

const pieceValue: Record<PieceType, number> = {
  p: 1,
  n: 3,
  b: 3,
  r: 5,
  q: 9,
  k: 0,
};

const game = new Chess();
const tiles = new Map<string, TileVisual>();
const pieces = new Map<string, PieceVisual>();

let selectedSquare: string | null = null;
let legalTargets = new Set<string>();
let elapsed = 0;
let cameraAlphaTarget = 0;

let engine: Engine;
let scene: Scene;
let camera: ArcRotateCamera;

function fileFromIndex(file: number): string {
  return String.fromCharCode('a'.charCodeAt(0) + file);
}

function rankFromIndex(rank: number): string {
  return `${rank + 1}`;
}

function squareName(file: number, rank: number): string {
  return `${fileFromIndex(file)}${rankFromIndex(rank)}`;
}

function squareToWorld(square: string): Vector3 {
  const file = square.charCodeAt(0) - 'a'.charCodeAt(0);
  const rank = Number.parseInt(square[1], 10) - 1;
  return new Vector3((file - 3.5) * TILE_SIZE, 0, (rank - 3.5) * TILE_SIZE);
}

function isLightTile(file: number, rank: number): boolean {
  return (file + rank) % 2 === 0;
}

async function createEngine(target: HTMLCanvasElement): Promise<Engine> {
  if ((navigator as Navigator & { gpu?: unknown }).gpu) {
    try {
      const webgpu = new WebGPUEngine(target, {
        antialias: true,
        adaptToDeviceRatio: true,
      });
      await webgpu.initAsync();
      return webgpu;
    } catch (err) {
      console.warn('WebGPU init failed, falling back to WebGL2.', err);
    }
  }
  return new Engine(target, true, {
    preserveDrawingBuffer: true,
    stencil: true,
  });
}

function buildScene(targetScene: Scene): void {
  targetScene.clearColor = new Color4(0.03, 0.05, 0.1, 1.0);

  const hemi = new HemisphericLight('hemi', new Vector3(0, 1, 0), targetScene);
  hemi.intensity = 0.68;
  hemi.diffuse = new Color3(0.9, 0.95, 1.0);
  hemi.groundColor = new Color3(0.15, 0.2, 0.3);

  const glow = new GlowLayer('glow', targetScene, { blurKernelSize: 36 });
  glow.intensity = 0.45;

  camera = new ArcRotateCamera('camera', Math.PI * 0.5, 1.07, 13.2, Vector3.Zero(), targetScene);
  camera.lowerBetaLimit = 0.92;
  camera.upperBetaLimit = 1.17;
  camera.lowerRadiusLimit = 11.6;
  camera.upperRadiusLimit = 14.5;
  camera.fov = 0.82;
  camera.detachControl();

  const boardPlateMat = new StandardMaterial('board-plate-mat', targetScene);
  boardPlateMat.diffuseColor = new Color3(0.05, 0.08, 0.16);
  boardPlateMat.specularColor = new Color3(0.18, 0.26, 0.42);
  boardPlateMat.emissiveColor = new Color3(0.015, 0.02, 0.04);

  const boardPlate = MeshBuilder.CreateBox('board-plate', {
    width: 9.2,
    depth: 9.2,
    height: 0.25,
  }, targetScene);
  boardPlate.position.y = -0.16;
  boardPlate.material = boardPlateMat;

  const frameMat = new StandardMaterial('frame-mat', targetScene);
  frameMat.diffuseColor = new Color3(0.08, 0.12, 0.2);
  frameMat.specularColor = new Color3(0.25, 0.42, 0.72);
  frameMat.emissiveColor = new Color3(0.05, 0.09, 0.16);

  const frame = MeshBuilder.CreateBox('frame', {
    width: 8.7,
    depth: 8.7,
    height: 0.08,
  }, targetScene);
  frame.position.y = -0.01;
  frame.material = frameMat;

  for (let rank = 0; rank < 8; rank += 1) {
    for (let file = 0; file < 8; file += 1) {
      const sq = squareName(file, rank);
      const tile = MeshBuilder.CreateBox(`tile-${sq}`, {
        width: 0.95,
        depth: 0.95,
        height: 0.08,
      }, targetScene);
      tile.position = squareToWorld(sq);
      tile.position.y = 0.045;

      const baseColor = isLightTile(file, rank)
        ? new Color3(0.75, 0.8, 0.92)
        : new Color3(0.14, 0.2, 0.32);
      const tileMat = new StandardMaterial(`tile-mat-${sq}`, targetScene);
      tileMat.diffuseColor = baseColor;
      tileMat.specularColor = new Color3(0.24, 0.34, 0.54);
      tileMat.emissiveColor = baseColor.scale(0.05);
      tile.material = tileMat;

      tile.metadata = { square: sq, kind: 'tile' };
      tiles.set(sq, { mesh: tile, material: tileMat, baseColor });
    }
  }

  targetScene.onPointerObservable.add((evt) => {
    if (evt.type !== PointerEventTypes.POINTERPICK) {
      return;
    }
    const pick = evt.pickInfo;
    if (!pick?.hit || !pick.pickedMesh) {
      return;
    }

    const picked = pick.pickedMesh as AbstractMesh;
    const square = picked.metadata?.square as string | undefined;
    if (!square) {
      return;
    }
    handleSquareClick(square);
  });
}

function clearPieceVisuals(): void {
  for (const piece of pieces.values()) {
    piece.mesh.dispose(false, true);
  }
  pieces.clear();
}

function pieceHeight(type: PieceType): number {
  switch (type) {
    case 'p':
      return 0.65;
    case 'n':
      return 0.92;
    case 'b':
      return 0.98;
    case 'r':
      return 1.02;
    case 'q':
      return 1.12;
    case 'k':
      return 1.22;
    default:
      return 0.9;
  }
}

function buildPieceVisual(square: string, type: PieceType, color: PieceColor): PieceVisual {
  const world = squareToWorld(square);
  const height = pieceHeight(type);
  const body = MeshBuilder.CreateCylinder(`piece-${square}-${type}`, {
    diameterTop: 0.34,
    diameterBottom: 0.46,
    height,
    tessellation: 14,
  }, scene);
  body.position = world.add(new Vector3(0, PIECE_BASE_Y + (height * 0.5), 0));

  const top = MeshBuilder.CreateSphere(`piece-top-${square}`, {
    diameter: 0.28,
    segments: 10,
  }, scene);
  top.position = body.position.add(new Vector3(0, (height * 0.46), 0));

  const merged = Mesh.MergeMeshes([body, top], true, true, undefined, false, true);
  if (!merged) {
    throw new Error('Failed to merge piece mesh.');
  }
  merged.metadata = { square, kind: 'piece' };

  const mat = new StandardMaterial(`piece-mat-${square}`, scene);
  if (color === 'w') {
    mat.diffuseColor = new Color3(0.93, 0.96, 1.0);
    mat.specularColor = new Color3(0.42, 0.54, 0.76);
    mat.emissiveColor = new Color3(0.04, 0.06, 0.09);
  } else {
    mat.diffuseColor = new Color3(0.08, 0.12, 0.19);
    mat.specularColor = new Color3(0.32, 0.4, 0.58);
    mat.emissiveColor = new Color3(0.02, 0.03, 0.06);
  }
  merged.material = mat;

  return {
    mesh: merged,
    square,
    type,
    color,
  };
}

function rebuildPieces(): void {
  clearPieceVisuals();
  const boardRows = game.board();

  for (let rank = 0; rank < boardRows.length; rank += 1) {
    const row = boardRows[rank];
    for (let file = 0; file < row.length; file += 1) {
      const piece = row[file];
      if (!piece) {
        continue;
      }

      const algebraic = squareName(file, 7 - rank);
      const visual = buildPieceVisual(algebraic, piece.type as PieceType, piece.color as PieceColor);
      pieces.set(algebraic, visual);
    }
  }
}

function cameraTargetAlpha(): number {
  return game.turn() === 'w' ? Math.PI * 0.5 : -Math.PI * 0.5;
}

function computeScoreText(): string {
  let white = 0;
  let black = 0;

  for (const row of game.board()) {
    for (const piece of row) {
      if (!piece) {
        continue;
      }
      const value = pieceValue[piece.type as PieceType] ?? 0;
      if (piece.color === 'w') {
        white += value;
      } else {
        black += value;
      }
    }
  }

  const diff = white - black;
  const evalText = diff === 0 ? 'Even' : diff > 0 ? `White +${diff}` : `Black +${Math.abs(diff)}`;
  return `Mat W:${white} B:${black} | ${evalText}`;
}

function computeStatusText(): string {
  if (game.isCheckmate()) {
    return game.turn() === 'w' ? 'Checkmate | Black wins' : 'Checkmate | White wins';
  }
  if (game.isStalemate()) {
    return 'Stalemate';
  }
  if (game.isDraw()) {
    return 'Draw';
  }
  const turn = game.turn() === 'w' ? 'White' : 'Black';
  return game.isCheck() ? `${turn} to move (Check)` : `${turn} to move`;
}

function updateHud(): void {
  statusText.textContent = computeStatusText();
  scoreText.textContent = computeScoreText();
}

function setTileHighlight(square: string, selected: boolean, legal: boolean, pulse: number): void {
  const tile = tiles.get(square);
  if (!tile) {
    return;
  }
  if (selected) {
    tile.material.emissiveColor = new Color3(0.75 + (pulse * 0.2), 0.46, 0.12);
    return;
  }
  if (legal) {
    tile.material.emissiveColor = new Color3(0.34 + (pulse * 0.1), 0.64 + (pulse * 0.1), 0.22);
    return;
  }
  tile.material.emissiveColor = tile.baseColor.scale(0.05);
}

function refreshHighlights(pulse: number): void {
  for (const square of tiles.keys()) {
    setTileHighlight(square, selectedSquare === square, legalTargets.has(square), pulse);
  }
}

function legalTargetsFrom(square: string): Set<string> {
  const targets = new Set<string>();
  for (const move of game.moves({ square, verbose: true })) {
    targets.add(move.to);
  }
  return targets;
}

function clearSelection(): void {
  selectedSquare = null;
  legalTargets.clear();
}

function handleSquareClick(square: string): void {
  const clickedPiece = game.get(square as Parameters<Chess['get']>[0]);
  const turn = game.turn();

  if (!selectedSquare) {
    if (clickedPiece && clickedPiece.color === turn) {
      selectedSquare = square;
      legalTargets = legalTargetsFrom(square);
    }
    return;
  }

  if (clickedPiece && clickedPiece.color === turn) {
    selectedSquare = square;
    legalTargets = legalTargetsFrom(square);
    return;
  }

  if (!legalTargets.has(square)) {
    clearSelection();
    return;
  }

  const move = game.move({
    from: selectedSquare,
    to: square,
    promotion: 'q',
  });

  clearSelection();
  if (!move) {
    return;
  }

  rebuildPieces();
  updateHud();
  cameraAlphaTarget = cameraTargetAlpha();
}

function tick(dt: number): void {
  elapsed += dt;
  const pulse = (Math.sin(elapsed * 4.0) + 1.0) * 0.5;

  const diff = cameraAlphaTarget - camera.alpha;
  camera.alpha += diff * Math.min(1.0, dt * 4.0);
  camera.beta += (1.05 - camera.beta) * Math.min(1.0, dt * 3.0);
  camera.radius += (12.8 - camera.radius) * Math.min(1.0, dt * 3.0);

  refreshHighlights(pulse);
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
    turn: game.turn(),
    status: computeStatusText(),
    score: computeScoreText(),
    selected_square: selectedSquare,
    legal_targets: Array.from(legalTargets).sort(),
    fen: game.fen(),
    pieces: Array.from(pieces.values()).map((p) => ({
      square: p.square,
      type: p.type,
      color: p.color,
      x: Number(p.mesh.position.x.toFixed(3)),
      y: Number(p.mesh.position.y.toFixed(3)),
      z: Number(p.mesh.position.z.toFixed(3)),
    })),
  };
  return JSON.stringify(payload);
}

(window as Window & { render_game_to_text?: () => string; advanceTime?: (ms: number) => Promise<void> }).render_game_to_text = textState;
(window as Window & { render_game_to_text?: () => string; advanceTime?: (ms: number) => Promise<void> }).advanceTime = async (ms: number) => {
  const steps = Math.max(1, Math.round(ms / (1000 / 60)));
  for (let i = 0; i < steps; i += 1) {
    tick(1 / 60);
  }
  scene.render();
};

async function start(): Promise<void> {
  engine = await createEngine(canvas);
  scene = new Scene(engine);

  buildScene(scene);
  rebuildPieces();
  updateHud();
  cameraAlphaTarget = cameraTargetAlpha();
  refreshHighlights(0.0);

  let last = performance.now();
  engine.runRenderLoop(() => {
    const now = performance.now();
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    tick(dt);
    scene.render();
  });

  window.addEventListener('resize', () => {
    engine.resize();
  });
}

void start();
