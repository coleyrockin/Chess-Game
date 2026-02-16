import { AbstractMesh } from '@babylonjs/core/Meshes/abstractMesh';
import { ArcRotateCamera } from '@babylonjs/core/Cameras/arcRotateCamera';
import { Color3, Color4, Vector3 } from '@babylonjs/core/Maths/math';
import { AbstractEngine } from '@babylonjs/core/Engines/abstractEngine';
import { GlowLayer } from '@babylonjs/core/Layers/glowLayer';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { Mesh } from '@babylonjs/core/Meshes/mesh';
import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import { PointerEventTypes } from '@babylonjs/core/Events/pointerEvents';
import { Scene } from '@babylonjs/core/scene';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { DynamicTexture } from '@babylonjs/core/Materials/Textures/dynamicTexture';
import '@babylonjs/core/Culling/ray';

import { BOARD_FILES, BOARD_RANKS, isValidSquare, squareName, squareToIndices } from './chessCoordinates';
import type { BoardPiece, PieceColor, PieceType } from './chessGameController';

export const TILE_SIZE = 1.0;
export const PIECE_BASE_Y = 0.35;

type TileVisual = {
  mesh: Mesh;
  material: StandardMaterial;
  baseColor: Color3;
};

type PieceVisual = {
  mesh: Mesh;
  material: StandardMaterial;
  square: string;
  type: PieceType;
  color: PieceColor;
};

const BOARD_HALF_EXTENT = 4.0;

function isLightTile(file: number, rank: number): boolean {
  return (file + rank) % 2 === 0;
}

function pieceAccent(type: PieceType): Color3 {
  switch (type) {
    case 'p':
      return new Color3(0.24, 0.72, 0.95);
    case 'n':
      return new Color3(0.99, 0.56, 0.26);
    case 'b':
      return new Color3(0.44, 0.92, 0.58);
    case 'r':
      return new Color3(0.98, 0.83, 0.3);
    case 'q':
      return new Color3(0.86, 0.5, 0.96);
    case 'k':
      return new Color3(0.97, 0.42, 0.4);
    default:
      return new Color3(0.75, 0.75, 0.82);
  }
}

export function squareToWorld(square: string): Vector3 {
  const { file, rank } = squareToIndices(square);
  return new Vector3((file - 3.5) * TILE_SIZE, 0, (rank - 3.5) * TILE_SIZE);
}

export function pieceHeight(type: PieceType): number {
  switch (type) {
    case 'p':
      return 0.72;
    case 'n':
      return 1.02;
    case 'b':
      return 1.1;
    case 'r':
      return 1.0;
    case 'q':
      return 1.22;
    case 'k':
      return 1.3;
    default:
      return 1.0;
  }
}

export class BoardScene {
  readonly scene: Scene;

  private static readonly POINTER_DEDUP_MS = 64;

  private static readonly WHITE_ALPHA = -Math.PI * 0.5;

  private static readonly BLACK_ALPHA = Math.PI * 0.5;

  private readonly camera: ArcRotateCamera;

  private readonly canvas: HTMLCanvasElement;

  private readonly tiles = new Map<string, TileVisual>();

  private readonly pieces = new Map<string, PieceVisual>();

  private elapsed = 0;

  private activeTurn: PieceColor = 'w';

  private cameraAlphaTarget = BoardScene.WHITE_ALPHA;

  private cameraBetaTarget = 1.03;

  private cameraRadiusTarget = 12.6;

  private lastPointerHandledAt = -Infinity;

  constructor(
    private readonly engine: AbstractEngine,
    private readonly onSquareClick: (square: string) => void,
  ) {
    const canvas = this.engine.getRenderingCanvas();
    if (!(canvas instanceof HTMLCanvasElement)) {
      throw new Error('Expected HTMLCanvasElement rendering target.');
    }
    this.canvas = canvas;

    this.scene = new Scene(engine);
    this.scene.clearColor = new Color4(0.02, 0.04, 0.09, 1.0);

    this.camera = new ArcRotateCamera(
      'camera',
      BoardScene.WHITE_ALPHA,
      this.cameraBetaTarget,
      this.cameraRadiusTarget,
      new Vector3(0, 0.25, 0),
      this.scene,
    );
    this.camera.lowerBetaLimit = 0.9;
    this.camera.upperBetaLimit = 1.2;
    this.camera.lowerRadiusLimit = 11.5;
    this.camera.upperRadiusLimit = 13.8;
    this.camera.fov = 0.78;
    this.camera.detachControl();

    this.configureLighting();
    this.buildBoard();
    this.registerPointerInput();
  }

  setTurn(turn: PieceColor): void {
    this.activeTurn = turn;
  }

  setPerspective(color: PieceColor): void {
    this.cameraAlphaTarget = color === 'w' ? BoardScene.WHITE_ALPHA : BoardScene.BLACK_ALPHA;
  }

  syncPieces(boardPieces: readonly BoardPiece[]): void {
    this.clearPieceVisuals();
    for (const boardPiece of boardPieces) {
      const visual = this.buildPieceVisual(boardPiece.square, boardPiece.type, boardPiece.color);
      this.pieces.set(boardPiece.square, visual);
    }
  }

  update(dt: number, selectedSquare: string | null, legalTargets: ReadonlySet<string>): void {
    this.elapsed += dt;
    const pulse = (Math.sin(this.elapsed * 4.0) + 1.0) * 0.5;

    const alphaDelta = this.cameraAlphaTarget - this.camera.alpha;
    this.camera.alpha += alphaDelta * Math.min(1.0, dt * 5.0);
    this.camera.beta += (this.cameraBetaTarget - this.camera.beta) * Math.min(1.0, dt * 4.0);
    this.camera.radius += (this.cameraRadiusTarget - this.camera.radius) * Math.min(1.0, dt * 4.0);

    this.refreshHighlights(selectedSquare, legalTargets, pulse);
  }

  render(): void {
    this.scene.render();
  }

  resize(): void {
    this.engine.resize();
  }

  private configureLighting(): void {
    const hemi = new HemisphericLight('hemi', new Vector3(0, 1, 0), this.scene);
    hemi.intensity = 0.65;
    hemi.diffuse = new Color3(0.9, 0.95, 1.0);
    hemi.groundColor = new Color3(0.13, 0.16, 0.22);

    const keyLight = new DirectionalLight('key', new Vector3(-0.8, -1.0, 0.5), this.scene);
    keyLight.position = new Vector3(10, 12, -8);
    keyLight.intensity = 0.48;
    keyLight.diffuse = new Color3(0.78, 0.84, 1.0);

    const rimLight = new DirectionalLight('rim', new Vector3(0.8, -1.0, -0.4), this.scene);
    rimLight.position = new Vector3(-10, 10, 9);
    rimLight.intensity = 0.28;
    rimLight.diffuse = new Color3(0.35, 0.52, 0.88);

    const glow = new GlowLayer('glow', this.scene, { blurKernelSize: 32 });
    glow.intensity = 0.36;
  }

  private buildBoard(): void {
    const pedestalMat = new StandardMaterial('pedestal-mat', this.scene);
    pedestalMat.diffuseColor = new Color3(0.07, 0.1, 0.18);
    pedestalMat.specularColor = new Color3(0.2, 0.26, 0.42);
    pedestalMat.emissiveColor = new Color3(0.02, 0.03, 0.06);

    const pedestal = MeshBuilder.CreateBox(
      'board-pedestal',
      {
        width: 10.0,
        depth: 10.0,
        height: 0.36,
      },
      this.scene,
    );
    pedestal.position.y = -0.29;
    pedestal.material = pedestalMat;

    const frameMat = new StandardMaterial('frame-mat', this.scene);
    frameMat.diffuseColor = new Color3(0.14, 0.19, 0.3);
    frameMat.specularColor = new Color3(0.34, 0.48, 0.75);
    frameMat.emissiveColor = new Color3(0.05, 0.08, 0.16);

    const frame = MeshBuilder.CreateBox(
      'board-frame',
      {
        width: 8.82,
        depth: 8.82,
        height: 0.1,
      },
      this.scene,
    );
    frame.position.y = -0.02;
    frame.material = frameMat;

    for (let rank = 0; rank < BOARD_RANKS; rank += 1) {
      for (let file = 0; file < BOARD_FILES; file += 1) {
        const square = squareName(file, rank);
        const tile = MeshBuilder.CreateBox(
          `tile-${square}`,
          {
            width: 0.95,
            depth: 0.95,
            height: 0.085,
          },
          this.scene,
        );
        tile.position = squareToWorld(square);
        tile.position.y = 0.045;

        const baseColor = isLightTile(file, rank)
          ? new Color3(0.78, 0.83, 0.93)
          : new Color3(0.16, 0.23, 0.35);

        const tileMat = new StandardMaterial(`tile-mat-${square}`, this.scene);
        tileMat.diffuseColor = baseColor;
        tileMat.specularColor = new Color3(0.25, 0.34, 0.52);
        tileMat.emissiveColor = baseColor.scale(0.05);
        tile.material = tileMat;

        tile.metadata = { square, kind: 'tile' };
        this.tiles.set(square, { mesh: tile, material: tileMat, baseColor });
      }
    }

    this.buildCoordinateLabels();
  }

  private buildCoordinateLabels(): void {
    for (let file = 0; file < BOARD_FILES; file += 1) {
      const label = String.fromCharCode('A'.charCodeAt(0) + file);
      const x = (file - 3.5) * TILE_SIZE;
      this.createCoordinateLabel(label, new Vector3(x, 0.14, -4.46), 0);
      this.createCoordinateLabel(label, new Vector3(x, 0.14, 4.46), Math.PI);
    }

    for (let rank = 0; rank < BOARD_RANKS; rank += 1) {
      const label = `${rank + 1}`;
      const z = (rank - 3.5) * TILE_SIZE;
      this.createCoordinateLabel(label, new Vector3(-4.46, 0.14, z), Math.PI * 0.5);
      this.createCoordinateLabel(label, new Vector3(4.46, 0.14, z), -Math.PI * 0.5);
    }
  }

  private createCoordinateLabel(text: string, position: Vector3, rotationY: number): void {
    const texture = new DynamicTexture(`coord-${text}-${position.x}-${position.z}`, { width: 256, height: 256 }, this.scene);
    texture.hasAlpha = true;
    texture.drawText(text, null, 176, 'bold 158px Rajdhani', '#d8e8ff', 'transparent', true, true);

    const mat = new StandardMaterial(`coord-mat-${text}-${position.x}-${position.z}`, this.scene);
    mat.diffuseTexture = texture;
    mat.opacityTexture = texture;
    mat.emissiveColor = new Color3(0.25, 0.38, 0.68);
    mat.specularColor = Color3.Black();
    mat.backFaceCulling = false;

    const plane = MeshBuilder.CreatePlane(`coord-${text}-${position.x}-${position.z}`, { size: 0.34 }, this.scene);
    plane.position = position;
    plane.rotation = new Vector3(Math.PI * 0.5, rotationY, 0);
    plane.material = mat;
  }

  private registerPointerInput(): void {
    const handlePick = (
      pick: { hit: boolean; pickedMesh?: AbstractMesh | null; pickedPoint?: Vector3 | null } | null | undefined,
    ): void => {
      const square = this.resolveSquareFromPick(pick);
      if (!square) {
        return;
      }
      this.lastPointerHandledAt = performance.now();
      this.onSquareClick(square);
    };

    this.scene.onPointerObservable.add((evt) => {
      if (evt.type !== PointerEventTypes.POINTERPICK && evt.type !== PointerEventTypes.POINTERTAP) {
        return;
      }
      handlePick(
        evt.pickInfo as { hit: boolean; pickedMesh?: AbstractMesh | null; pickedPoint?: Vector3 | null } | null | undefined,
      );
    });

    // Fallback for browsers that do not fire Babylon pointer observables reliably.
    this.canvas.addEventListener('click', (event) => {
      const now = performance.now();
      if (now - this.lastPointerHandledAt < BoardScene.POINTER_DEDUP_MS) {
        return;
      }

      const rect = this.canvas.getBoundingClientRect();
      const cssX = event.clientX - rect.left;
      const cssY = event.clientY - rect.top;
      const renderX = (cssX / rect.width) * this.engine.getRenderWidth();
      const renderY = (cssY / rect.height) * this.engine.getRenderHeight();

      const square = this.resolveSquareFromCanvasPosition(renderX, renderY);
      if (!square) {
        return;
      }
      this.onSquareClick(square);
    });
  }

  private resolveSquareFromCanvasPosition(renderX: number, renderY: number): string | null {
    const pick = this.scene.pick(renderX, renderY) as
      | { hit: boolean; pickedMesh?: AbstractMesh | null; pickedPoint?: Vector3 | null }
      | null
      | undefined;
    const fromPick = this.resolveSquareFromPick(pick);
    if (fromPick) {
      return fromPick;
    }

    const ray = this.scene.createPickingRay(renderX, renderY, null, this.camera);
    if (Math.abs(ray.direction.y) < 1e-6) {
      return null;
    }

    const boardY = 0.045;
    const t = (boardY - ray.origin.y) / ray.direction.y;
    if (t <= 0) {
      return null;
    }

    const point = ray.origin.add(ray.direction.scale(t));
    return this.squareFromBoardPosition(point.x, point.z);
  }

  private resolveSquareFromPick(
    pick: { hit: boolean; pickedMesh?: AbstractMesh | null; pickedPoint?: Vector3 | null } | null | undefined,
  ): string | null {
    if (!pick?.hit) {
      return null;
    }

    let mesh = pick.pickedMesh ?? null;
    while (mesh) {
      const square = mesh.metadata?.square as string | undefined;
      if (square && isValidSquare(square)) {
        return square;
      }
      mesh = mesh.parent as AbstractMesh | null;
    }

    if (!pick.pickedPoint) {
      return null;
    }
    return this.squareFromBoardPosition(pick.pickedPoint.x, pick.pickedPoint.z);
  }

  private squareFromBoardPosition(x: number, z: number): string | null {
    if (x <= -BOARD_HALF_EXTENT || x >= BOARD_HALF_EXTENT || z <= -BOARD_HALF_EXTENT || z >= BOARD_HALF_EXTENT) {
      return null;
    }

    const file = Math.floor(x + BOARD_HALF_EXTENT);
    const rank = Math.floor(z + BOARD_HALF_EXTENT);
    if (file < 0 || file > 7 || rank < 0 || rank > 7) {
      return null;
    }

    return squareName(file, rank);
  }

  private clearPieceVisuals(): void {
    for (const piece of this.pieces.values()) {
      piece.mesh.dispose(false, true);
      piece.material.dispose(false, true);
    }
    this.pieces.clear();
  }

  private buildPieceVisual(square: string, type: PieceType, color: PieceColor): PieceVisual {
    const world = squareToWorld(square);
    const parts: Mesh[] = [];
    const nameRoot = `piece-${square}-${type}`;

    const makeCylinder = (
      name: string,
      diameterTop: number,
      diameterBottom: number,
      height: number,
      y: number,
      x = 0,
      z = 0,
    ): Mesh => {
      const mesh = MeshBuilder.CreateCylinder(
        name,
        {
          diameterTop,
          diameterBottom,
          height,
          tessellation: 28,
        },
        this.scene,
      );
      mesh.position = world.add(new Vector3(x, y, z));
      parts.push(mesh);
      return mesh;
    };

    const makeSphere = (name: string, diameter: number, y: number, x = 0, z = 0): Mesh => {
      const mesh = MeshBuilder.CreateSphere(
        name,
        {
          diameter,
          segments: 14,
        },
        this.scene,
      );
      mesh.position = world.add(new Vector3(x, y, z));
      parts.push(mesh);
      return mesh;
    };

    const makeBox = (
      name: string,
      width: number,
      height: number,
      depth: number,
      y: number,
      x = 0,
      z = 0,
      rotX = 0,
      rotY = 0,
      rotZ = 0,
    ): Mesh => {
      const mesh = MeshBuilder.CreateBox(
        name,
        {
          width,
          height,
          depth,
        },
        this.scene,
      );
      mesh.position = world.add(new Vector3(x, y, z));
      mesh.rotation = new Vector3(rotX, rotY, rotZ);
      parts.push(mesh);
      return mesh;
    };

    const makeTorus = (name: string, diameter: number, thickness: number, y: number): Mesh => {
      const mesh = MeshBuilder.CreateTorus(
        name,
        {
          diameter,
          thickness,
          tessellation: 28,
        },
        this.scene,
      );
      mesh.position = world.add(new Vector3(0, y, 0));
      parts.push(mesh);
      return mesh;
    };

    makeCylinder(`${nameRoot}-base`, 0.44, 0.6, 0.18, PIECE_BASE_Y + 0.09);
    makeTorus(`${nameRoot}-base-ring`, 0.43, 0.045, PIECE_BASE_Y + 0.2);

    switch (type) {
      case 'p':
        makeCylinder(`${nameRoot}-body`, 0.22, 0.3, 0.38, PIECE_BASE_Y + 0.39);
        makeTorus(`${nameRoot}-collar`, 0.28, 0.032, PIECE_BASE_Y + 0.55);
        makeSphere(`${nameRoot}-head`, 0.24, PIECE_BASE_Y + 0.69);
        break;
      case 'n': {
        const forward = color === 'w' ? 1 : -1;
        makeCylinder(`${nameRoot}-neck-base`, 0.24, 0.34, 0.35, PIECE_BASE_Y + 0.38);
        makeBox(`${nameRoot}-neck`, 0.22, 0.52, 0.34, PIECE_BASE_Y + 0.63, 0, 0.03 * forward, 0.2 * forward);
        makeBox(`${nameRoot}-head`, 0.2, 0.22, 0.22, PIECE_BASE_Y + 0.86, 0, 0.14 * forward, 0.04 * forward);
        makeBox(`${nameRoot}-snout`, 0.13, 0.09, 0.12, PIECE_BASE_Y + 0.77, 0, 0.22 * forward, 0.18 * forward);
        makeCylinder(`${nameRoot}-ear-left`, 0.0, 0.055, 0.11, PIECE_BASE_Y + 0.98, 0.05, 0.15 * forward);
        makeCylinder(`${nameRoot}-ear-right`, 0.0, 0.055, 0.11, PIECE_BASE_Y + 0.98, -0.05, 0.15 * forward);
        break;
      }
      case 'b':
        makeCylinder(`${nameRoot}-body`, 0.17, 0.34, 0.65, PIECE_BASE_Y + 0.52);
        makeTorus(`${nameRoot}-collar`, 0.28, 0.032, PIECE_BASE_Y + 0.72);
        makeSphere(`${nameRoot}-crown`, 0.24, PIECE_BASE_Y + 0.91);
        makeCylinder(`${nameRoot}-spire`, 0.0, 0.06, 0.12, PIECE_BASE_Y + 1.05);
        break;
      case 'r':
        makeCylinder(`${nameRoot}-tower`, 0.31, 0.38, 0.64, PIECE_BASE_Y + 0.52);
        makeCylinder(`${nameRoot}-cap`, 0.36, 0.36, 0.08, PIECE_BASE_Y + 0.83);
        makeBox(`${nameRoot}-battlement-n`, 0.09, 0.15, 0.12, PIECE_BASE_Y + 0.92, 0, 0.145);
        makeBox(`${nameRoot}-battlement-s`, 0.09, 0.15, 0.12, PIECE_BASE_Y + 0.92, 0, -0.145);
        makeBox(`${nameRoot}-battlement-e`, 0.12, 0.15, 0.09, PIECE_BASE_Y + 0.92, 0.145, 0);
        makeBox(`${nameRoot}-battlement-w`, 0.12, 0.15, 0.09, PIECE_BASE_Y + 0.92, -0.145, 0);
        break;
      case 'q':
        makeCylinder(`${nameRoot}-body`, 0.2, 0.36, 0.72, PIECE_BASE_Y + 0.55);
        makeTorus(`${nameRoot}-waist`, 0.29, 0.03, PIECE_BASE_Y + 0.77);
        makeTorus(`${nameRoot}-crown-ring`, 0.3, 0.03, PIECE_BASE_Y + 0.99);
        for (let i = 0; i < 6; i += 1) {
          const angle = (i / 6) * Math.PI * 2;
          makeSphere(`${nameRoot}-crown-jewel-${i}`, 0.07, PIECE_BASE_Y + 1.07, Math.cos(angle) * 0.11, Math.sin(angle) * 0.11);
        }
        makeSphere(`${nameRoot}-crown-top`, 0.1, PIECE_BASE_Y + 1.15);
        break;
      case 'k':
        makeCylinder(`${nameRoot}-body`, 0.2, 0.36, 0.78, PIECE_BASE_Y + 0.58);
        makeTorus(`${nameRoot}-crown-ring`, 0.28, 0.03, PIECE_BASE_Y + 0.98);
        makeBox(`${nameRoot}-cross-post`, 0.055, 0.27, 0.055, PIECE_BASE_Y + 1.12);
        makeBox(`${nameRoot}-cross-bar`, 0.17, 0.045, 0.05, PIECE_BASE_Y + 1.2);
        makeSphere(`${nameRoot}-crown-top`, 0.08, PIECE_BASE_Y + 1.01);
        break;
      default:
        makeCylinder(`${nameRoot}-fallback`, 0.22, 0.32, 0.56, PIECE_BASE_Y + 0.47);
    }

    const merged = Mesh.MergeMeshes(parts, true, true, undefined, false, true);
    if (!merged) {
      throw new Error('Failed to merge piece mesh.');
    }

    merged.metadata = { square, kind: 'piece' };

    const accent = pieceAccent(type);
    const material = new StandardMaterial(`piece-mat-${square}`, this.scene);
    if (color === 'w') {
      material.diffuseColor = new Color3(0.96, 0.97, 1.0);
      material.specularColor = new Color3(0.82, 0.9, 0.99);
      material.specularPower = 120;
      material.emissiveColor = accent.scale(0.1);
    } else {
      material.diffuseColor = new Color3(0.08, 0.11, 0.16);
      material.specularColor = new Color3(0.5, 0.6, 0.75);
      material.specularPower = 98;
      material.emissiveColor = accent.scale(0.055);
    }
    merged.material = material;

    return {
      mesh: merged,
      material,
      square,
      type,
      color,
    };
  }

  private refreshHighlights(selectedSquare: string | null, legalTargets: ReadonlySet<string>, pulse: number): void {
    for (const [square, tile] of this.tiles.entries()) {
      if (selectedSquare === square) {
        tile.material.emissiveColor = new Color3(0.8 + (pulse * 0.2), 0.48, 0.15);
      } else if (legalTargets.has(square)) {
        tile.material.emissiveColor = new Color3(0.32 + (pulse * 0.15), 0.72 + (pulse * 0.12), 0.26);
      } else {
        tile.material.emissiveColor = tile.baseColor.scale(0.05);
      }
    }

    for (const [square, visual] of this.pieces.entries()) {
      const accent = pieceAccent(visual.type);
      const isSelected = selectedSquare === square;
      if (isSelected) {
        visual.material.emissiveColor = accent.scale(0.22 + (pulse * 0.12));
      } else if (visual.color === this.activeTurn) {
        visual.material.emissiveColor = accent.scale(0.08);
      } else {
        visual.material.emissiveColor = accent.scale(0.05);
      }
    }
  }
}
