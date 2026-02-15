import { AbstractMesh } from '@babylonjs/core/Meshes/abstractMesh';
import { ArcRotateCamera } from '@babylonjs/core/Cameras/arcRotateCamera';
import { Color3, Color4, Vector3 } from '@babylonjs/core/Maths/math';
import { AbstractEngine } from '@babylonjs/core/Engines/abstractEngine';
import { GlowLayer } from '@babylonjs/core/Layers/glowLayer';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { Mesh } from '@babylonjs/core/Meshes/mesh';
import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import { PointerEventTypes } from '@babylonjs/core/Events/pointerEvents';
import { Scene } from '@babylonjs/core/scene';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';

import { squareName, squareToIndices } from './chessCoordinates';
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
  square: string;
  type: PieceType;
  color: PieceColor;
};

function isLightTile(file: number, rank: number): boolean {
  return (file + rank) % 2 === 0;
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
      return 1.0;
    case 'b':
      return 1.08;
    case 'r':
      return 1.0;
    case 'q':
      return 1.2;
    case 'k':
      return 1.28;
    default:
      return 1.0;
  }
}

export class BoardScene {
  readonly scene: Scene;

  private readonly camera: ArcRotateCamera;

  private readonly canvas: HTMLCanvasElement;

  private readonly tiles = new Map<string, TileVisual>();

  private readonly pieces = new Map<string, PieceVisual>();

  private elapsed = 0;

  private cameraAlphaTarget = Math.PI * 0.5;

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
    this.scene.clearColor = new Color4(0.03, 0.05, 0.1, 1.0);

    const hemi = new HemisphericLight('hemi', new Vector3(0, 1, 0), this.scene);
    hemi.intensity = 0.68;
    hemi.diffuse = new Color3(0.9, 0.95, 1.0);
    hemi.groundColor = new Color3(0.15, 0.2, 0.3);

    const glow = new GlowLayer('glow', this.scene, { blurKernelSize: 36 });
    glow.intensity = 0.45;

    this.camera = new ArcRotateCamera('camera', Math.PI * 0.5, 1.07, 13.2, Vector3.Zero(), this.scene);
    this.camera.lowerBetaLimit = 0.92;
    this.camera.upperBetaLimit = 1.17;
    this.camera.lowerRadiusLimit = 11.6;
    this.camera.upperRadiusLimit = 14.5;
    this.camera.fov = 0.82;
    this.camera.detachControl();

    this.buildBoard();
    this.registerPointerInput();
  }

  setTurn(turn: PieceColor): void {
    this.cameraAlphaTarget = turn === 'w' ? Math.PI * 0.5 : -Math.PI * 0.5;
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
    this.camera.alpha += alphaDelta * Math.min(1.0, dt * 4.0);
    this.camera.beta += (1.05 - this.camera.beta) * Math.min(1.0, dt * 3.0);
    this.camera.radius += (12.8 - this.camera.radius) * Math.min(1.0, dt * 3.0);

    this.refreshHighlights(selectedSquare, legalTargets, pulse);
  }

  render(): void {
    this.scene.render();
  }

  resize(): void {
    this.engine.resize();
  }

  private buildBoard(): void {
    const boardPlateMat = new StandardMaterial('board-plate-mat', this.scene);
    boardPlateMat.diffuseColor = new Color3(0.05, 0.08, 0.16);
    boardPlateMat.specularColor = new Color3(0.18, 0.26, 0.42);
    boardPlateMat.emissiveColor = new Color3(0.015, 0.02, 0.04);

    const boardPlate = MeshBuilder.CreateBox(
      'board-plate',
      {
        width: 9.2,
        depth: 9.2,
        height: 0.25,
      },
      this.scene,
    );
    boardPlate.position.y = -0.16;
    boardPlate.material = boardPlateMat;

    const frameMat = new StandardMaterial('frame-mat', this.scene);
    frameMat.diffuseColor = new Color3(0.08, 0.12, 0.2);
    frameMat.specularColor = new Color3(0.25, 0.42, 0.72);
    frameMat.emissiveColor = new Color3(0.05, 0.09, 0.16);

    const frame = MeshBuilder.CreateBox(
      'frame',
      {
        width: 8.7,
        depth: 8.7,
        height: 0.08,
      },
      this.scene,
    );
    frame.position.y = -0.01;
    frame.material = frameMat;

    for (let rank = 0; rank < 8; rank += 1) {
      for (let file = 0; file < 8; file += 1) {
        const square = squareName(file, rank);
        const tile = MeshBuilder.CreateBox(
          `tile-${square}`,
          {
            width: 0.95,
            depth: 0.95,
            height: 0.08,
          },
          this.scene,
        );
        tile.position = squareToWorld(square);
        tile.position.y = 0.045;

        const baseColor = isLightTile(file, rank)
          ? new Color3(0.75, 0.8, 0.92)
          : new Color3(0.14, 0.2, 0.32);

        const tileMat = new StandardMaterial(`tile-mat-${square}`, this.scene);
        tileMat.diffuseColor = baseColor;
        tileMat.specularColor = new Color3(0.24, 0.34, 0.54);
        tileMat.emissiveColor = baseColor.scale(0.05);
        tile.material = tileMat;

        tile.metadata = { square, kind: 'tile' };
        this.tiles.set(square, { mesh: tile, material: tileMat, baseColor });
      }
    }
  }

  private registerPointerInput(): void {
    this.scene.onPointerObservable.add((evt) => {
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

      this.onSquareClick(square);
    });

    // Fallback for environments where pointer observables don't fire reliably.
    this.canvas.addEventListener('click', (event) => {
      const rect = this.canvas.getBoundingClientRect();
      const cssX = event.clientX - rect.left;
      const cssY = event.clientY - rect.top;
      const scale = this.engine.getHardwareScalingLevel();

      const pick = this.scene.pick(cssX / scale, cssY / scale);
      if (!pick?.hit || !pick.pickedMesh) {
        return;
      }

      const square = (pick.pickedMesh as AbstractMesh).metadata?.square as string | undefined;
      if (!square) {
        return;
      }

      this.onSquareClick(square);
    });
  }

  private clearPieceVisuals(): void {
    for (const piece of this.pieces.values()) {
      piece.mesh.dispose(false, true);
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
    ): Mesh => {
      const mesh = MeshBuilder.CreateCylinder(
        name,
        {
          diameterTop,
          diameterBottom,
          height,
          tessellation: 20,
        },
        this.scene,
      );
      mesh.position = world.add(new Vector3(0, y, 0));
      parts.push(mesh);
      return mesh;
    };

    const makeSphere = (name: string, diameter: number, y: number, x = 0, z = 0): Mesh => {
      const mesh = MeshBuilder.CreateSphere(
        name,
        {
          diameter,
          segments: 12,
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
          tessellation: 24,
        },
        this.scene,
      );
      mesh.position = world.add(new Vector3(0, y, 0));
      parts.push(mesh);
      return mesh;
    };

    // Shared base profile so all pieces look like a coherent set.
    makeCylinder(`${nameRoot}-pedestal`, 0.42, 0.56, 0.18, PIECE_BASE_Y + 0.09);
    makeTorus(`${nameRoot}-pedestal-ring`, 0.42, 0.05, PIECE_BASE_Y + 0.2);

    switch (type) {
      case 'p':
        makeCylinder(`${nameRoot}-body`, 0.2, 0.3, 0.36, PIECE_BASE_Y + 0.38);
        makeTorus(`${nameRoot}-collar`, 0.28, 0.035, PIECE_BASE_Y + 0.53);
        makeSphere(`${nameRoot}-head`, 0.24, PIECE_BASE_Y + 0.67);
        break;
      case 'n':
        makeCylinder(`${nameRoot}-neck-base`, 0.24, 0.34, 0.34, PIECE_BASE_Y + 0.38);
        makeBox(`${nameRoot}-neck`, 0.23, 0.52, 0.34, PIECE_BASE_Y + 0.62, 0, 0.04, 0.22, 0, 0);
        makeBox(`${nameRoot}-head`, 0.2, 0.22, 0.22, PIECE_BASE_Y + 0.86, 0, 0.18, 0.04, 0, 0);
        makeBox(`${nameRoot}-snout`, 0.13, 0.09, 0.12, PIECE_BASE_Y + 0.77, 0, 0.28, 0.18, 0, 0);
        makeCylinder(`${nameRoot}-ear-left`, 0.0, 0.055, 0.11, PIECE_BASE_Y + 0.98);
        parts[parts.length - 1].position.x += 0.05;
        parts[parts.length - 1].position.z += 0.2;
        makeCylinder(`${nameRoot}-ear-right`, 0.0, 0.055, 0.11, PIECE_BASE_Y + 0.98);
        parts[parts.length - 1].position.x -= 0.05;
        parts[parts.length - 1].position.z += 0.2;
        break;
      case 'b':
        makeCylinder(`${nameRoot}-body`, 0.16, 0.34, 0.64, PIECE_BASE_Y + 0.52);
        makeTorus(`${nameRoot}-collar`, 0.28, 0.03, PIECE_BASE_Y + 0.71);
        makeSphere(`${nameRoot}-crown`, 0.24, PIECE_BASE_Y + 0.9);
        makeCylinder(`${nameRoot}-spire`, 0.0, 0.06, 0.11, PIECE_BASE_Y + 1.04);
        break;
      case 'r':
        makeCylinder(`${nameRoot}-tower`, 0.3, 0.38, 0.64, PIECE_BASE_Y + 0.52);
        makeCylinder(`${nameRoot}-cap`, 0.36, 0.36, 0.07, PIECE_BASE_Y + 0.82);
        makeTorus(`${nameRoot}-cap-ring`, 0.37, 0.038, PIECE_BASE_Y + 0.84);
        makeBox(`${nameRoot}-battlement-n`, 0.09, 0.15, 0.12, PIECE_BASE_Y + 0.92, 0, 0.145);
        makeBox(`${nameRoot}-battlement-s`, 0.09, 0.15, 0.12, PIECE_BASE_Y + 0.92, 0, -0.145);
        makeBox(`${nameRoot}-battlement-e`, 0.12, 0.15, 0.09, PIECE_BASE_Y + 0.92, 0.145, 0);
        makeBox(`${nameRoot}-battlement-w`, 0.12, 0.15, 0.09, PIECE_BASE_Y + 0.92, -0.145, 0);
        break;
      case 'q':
        makeCylinder(`${nameRoot}-body`, 0.2, 0.36, 0.7, PIECE_BASE_Y + 0.55);
        makeTorus(`${nameRoot}-waist`, 0.29, 0.03, PIECE_BASE_Y + 0.76);
        makeTorus(`${nameRoot}-crown-ring`, 0.3, 0.03, PIECE_BASE_Y + 0.98);
        for (let i = 0; i < 6; i += 1) {
          const angle = (i / 6) * Math.PI * 2;
          makeSphere(
            `${nameRoot}-crown-jewel-${i}`,
            0.07,
            PIECE_BASE_Y + 1.06,
            Math.cos(angle) * 0.11,
            Math.sin(angle) * 0.11,
          );
        }
        makeSphere(`${nameRoot}-crown-top`, 0.1, PIECE_BASE_Y + 1.14);
        break;
      case 'k':
        makeCylinder(`${nameRoot}-body`, 0.2, 0.36, 0.76, PIECE_BASE_Y + 0.58);
        makeTorus(`${nameRoot}-crown-ring`, 0.28, 0.03, PIECE_BASE_Y + 0.97);
        makeBox(`${nameRoot}-cross-post`, 0.055, 0.27, 0.055, PIECE_BASE_Y + 1.1);
        makeBox(`${nameRoot}-cross-bar`, 0.17, 0.045, 0.05, PIECE_BASE_Y + 1.18);
        makeSphere(`${nameRoot}-crown-top`, 0.08, PIECE_BASE_Y + 1.0);
        break;
      default:
        makeCylinder(`${nameRoot}-fallback`, 0.22, 0.32, 0.56, PIECE_BASE_Y + 0.47);
    }

    const merged = Mesh.MergeMeshes(parts, true, true, undefined, false, true);
    if (!merged) {
      throw new Error('Failed to merge piece mesh.');
    }

    merged.metadata = { square, kind: 'piece' };

    const mat = new StandardMaterial(`piece-mat-${square}`, this.scene);
    const accentByType: Record<PieceType, Color3> = {
      p: new Color3(0.22, 0.72, 1.0),
      n: new Color3(0.99, 0.46, 0.24),
      b: new Color3(0.41, 0.94, 0.62),
      r: new Color3(0.94, 0.84, 0.3),
      q: new Color3(0.82, 0.48, 0.98),
      k: new Color3(0.98, 0.35, 0.35),
    };
    const accent = accentByType[type];

    if (color === 'w') {
      mat.diffuseColor = new Color3(0.95, 0.97, 1.0);
      mat.specularColor = new Color3(0.82, 0.88, 0.98);
      mat.emissiveColor = accent.scale(0.1);
      mat.specularPower = 110;
    } else {
      mat.diffuseColor = new Color3(0.08, 0.11, 0.17);
      mat.specularColor = new Color3(0.5, 0.58, 0.73);
      mat.emissiveColor = accent.scale(0.05);
      mat.specularPower = 95;
    }
    merged.material = mat;

    return {
      mesh: merged,
      square,
      type,
      color,
    };
  }

  private refreshHighlights(selectedSquare: string | null, legalTargets: ReadonlySet<string>, pulse: number): void {
    for (const [square, tile] of this.tiles.entries()) {
      if (selectedSquare === square) {
        tile.material.emissiveColor = new Color3(0.75 + (pulse * 0.2), 0.46, 0.12);
      } else if (legalTargets.has(square)) {
        tile.material.emissiveColor = new Color3(0.34 + (pulse * 0.1), 0.64 + (pulse * 0.1), 0.22);
      } else {
        tile.material.emissiveColor = tile.baseColor.scale(0.05);
      }
    }
  }
}
