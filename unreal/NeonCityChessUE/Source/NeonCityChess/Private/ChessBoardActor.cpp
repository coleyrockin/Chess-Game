#include "ChessBoardActor.h"

#include "ChessGameStateComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

AChessBoardActor::AChessBoardActor()
{
    PrimaryActorTick.bCanEverTick = false;

    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    LightTileInstances = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("LightTileInstances"));
    LightTileInstances->SetupAttachment(Root);
    LightTileInstances->SetCollisionEnabled(ECollisionEnabled::QueryOnly);

    DarkTileInstances = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("DarkTileInstances"));
    DarkTileInstances->SetupAttachment(Root);
    DarkTileInstances->SetCollisionEnabled(ECollisionEnabled::QueryOnly);

    WhitePieceInstances = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("WhitePieceInstances"));
    WhitePieceInstances->SetupAttachment(Root);
    WhitePieceInstances->SetCollisionEnabled(ECollisionEnabled::NoCollision);

    BlackPieceInstances = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("BlackPieceInstances"));
    BlackPieceInstances->SetupAttachment(Root);
    BlackPieceInstances->SetCollisionEnabled(ECollisionEnabled::NoCollision);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(
        TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (CubeMesh.Succeeded())
    {
        BoardMesh = CubeMesh.Object;
        LightTileInstances->SetStaticMesh(BoardMesh);
        DarkTileInstances->SetStaticMesh(BoardMesh);
        WhitePieceInstances->SetStaticMesh(BoardMesh);
        BlackPieceInstances->SetStaticMesh(BoardMesh);
    }

    static ConstructorHelpers::FObjectFinder<UMaterialInterface> BasicShapeMaterial(
        TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    if (BasicShapeMaterial.Succeeded())
    {
        TileMaterial = BasicShapeMaterial.Object;
    }
}

void AChessBoardActor::BeginPlay()
{
    Super::BeginPlay();
    TryResolveGameStateComponent();
    ApplyDefaultMaterials();
    RebuildVisuals();
    if (GameStateComponent != nullptr)
    {
        GameStateComponent->OnStateChanged.AddDynamic(this, &AChessBoardActor::HandleStateChanged);
    }
}

void AChessBoardActor::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    BuildBoardTiles();
}

FVector AChessBoardActor::SquareToWorld(const FString& Square, float HeightOffset) const
{
    const FString Normalized = NormalizeSquare(Square);
    if (!IsSquareValid(Normalized))
    {
        return BoardOrigin;
    }

    const int32 FileIndex = static_cast<int32>(Normalized[0] - TCHAR('a'));
    const int32 RankIndex = static_cast<int32>(Normalized[1] - TCHAR('1'));

    const float X = (static_cast<float>(FileIndex) - 3.5f) * TileSize;
    const float Y = (static_cast<float>(RankIndex) - 3.5f) * TileSize;
    return BoardOrigin + FVector(X, Y, HeightOffset);
}

bool AChessBoardActor::WorldToSquare(const FVector& WorldLocation, FString& OutSquare) const
{
    const FVector Local = WorldLocation - BoardOrigin;
    const int32 FileIndex = FMath::FloorToInt((Local.X / TileSize) + 4.0f);
    const int32 RankIndex = FMath::FloorToInt((Local.Y / TileSize) + 4.0f);
    if (FileIndex < 0 || FileIndex > 7 || RankIndex < 0 || RankIndex > 7)
    {
        return false;
    }

    const TCHAR File = static_cast<TCHAR>(TCHAR('a') + FileIndex);
    const TCHAR Rank = static_cast<TCHAR>(TCHAR('1') + RankIndex);
    OutSquare = FString::Printf(TEXT("%c%c"), File, Rank);
    return true;
}

bool AChessBoardActor::ClickWorldLocation(const FVector& WorldLocation, FString& OutError)
{
    OutError.Empty();

    if (GameStateComponent == nullptr)
    {
        OutError = TEXT("GameStateComponent is not set on ChessBoardActor.");
        return false;
    }

    FString Square;
    if (!WorldToSquare(WorldLocation, Square))
    {
        OutError = TEXT("Click is outside board bounds.");
        return false;
    }

    const FString Normalized = NormalizeSquare(Square);
    if (!GameStateComponent->CurrentState.SelectedSquare.IsEmpty() &&
        GameStateComponent->CurrentState.LegalTargets.Contains(Normalized))
    {
        return GameStateComponent->TryMoveSelectedTo(Normalized, OutError);
    }

    const bool bSelected = GameStateComponent->SelectSquare(Normalized);
    if (!bSelected)
    {
        OutError = FString::Printf(TEXT("Square %s is not selectable for current turn."), *Normalized);
    }
    return bSelected;
}

void AChessBoardActor::RebuildVisuals()
{
    BuildBoardTiles();
    if (GameStateComponent != nullptr)
    {
        RebuildPiecesFromFen(GameStateComponent->CurrentState.Fen);
    }
    else
    {
        WhitePieceInstances->ClearInstances();
        BlackPieceInstances->ClearInstances();
    }
}

void AChessBoardActor::HandleStateChanged()
{
    if (GameStateComponent == nullptr)
    {
        return;
    }
    RebuildPiecesFromFen(GameStateComponent->CurrentState.Fen);
}

bool AChessBoardActor::TryResolveGameStateComponent()
{
    if (GameStateComponent != nullptr)
    {
        return true;
    }

    if (UWorld* World = GetWorld())
    {
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (UChessGameStateComponent* Found = It->FindComponentByClass<UChessGameStateComponent>())
            {
                GameStateComponent = Found;
                return true;
            }
        }
    }
    return false;
}

void AChessBoardActor::BuildBoardTiles()
{
    LightTileInstances->ClearInstances();
    DarkTileInstances->ClearInstances();

    const float TileScaleXY = TileSize / 100.0f;
    const float TileScaleZ = TileThickness / 100.0f;
    const float TileCenterZ = TileThickness * 0.5f;

    for (int32 Rank = 0; Rank < 8; ++Rank)
    {
        for (int32 File = 0; File < 8; ++File)
        {
            const FVector Location = BoardOrigin + FVector(
                (static_cast<float>(File) - 3.5f) * TileSize,
                (static_cast<float>(Rank) - 3.5f) * TileSize,
                TileCenterZ);
            const FTransform TileTransform(FRotator::ZeroRotator, Location, FVector(TileScaleXY, TileScaleXY, TileScaleZ));
            const bool bLight = ((File + Rank) % 2) == 0;
            if (bLight)
            {
                LightTileInstances->AddInstance(TileTransform);
            }
            else
            {
                DarkTileInstances->AddInstance(TileTransform);
            }
        }
    }
}

void AChessBoardActor::RebuildPiecesFromFen(const FString& Fen)
{
    WhitePieceInstances->ClearInstances();
    BlackPieceInstances->ClearInstances();

    FString BoardFen = Fen;
    FString Ignored;
    if (Fen.Split(TEXT(" "), &BoardFen, &Ignored))
    {
        BoardFen = BoardFen.TrimStartAndEnd();
    }
    if (BoardFen.IsEmpty())
    {
        return;
    }

    TArray<FString> RankRows;
    BoardFen.ParseIntoArray(RankRows, TEXT("/"), true);
    if (RankRows.Num() != 8)
    {
        return;
    }

    for (int32 FenRow = 0; FenRow < RankRows.Num(); ++FenRow)
    {
        const FString& Row = RankRows[FenRow];
        const int32 BoardRank = 7 - FenRow;
        int32 File = 0;

        for (int32 CharIndex = 0; CharIndex < Row.Len(); ++CharIndex)
        {
            const TCHAR Symbol = Row[CharIndex];
            if (FChar::IsDigit(Symbol))
            {
                File += static_cast<int32>(Symbol - TCHAR('0'));
                continue;
            }
            if (File < 0 || File > 7)
            {
                break;
            }

            const bool bWhite = FChar::IsUpper(Symbol);
            const float ScaleFactor = PieceScaleForFenSymbol(Symbol);
            const float PieceWidth = PieceBaseSize * ScaleFactor;
            const float PieceHeight = PieceBaseHeight * ScaleFactor;

            const FVector Location = BoardOrigin + FVector(
                (static_cast<float>(File) - 3.5f) * TileSize,
                (static_cast<float>(BoardRank) - 3.5f) * TileSize,
                TileThickness + (PieceHeight * 0.5f));

            const FVector Scale(PieceWidth / 100.0f, PieceWidth / 100.0f, PieceHeight / 100.0f);
            const FTransform PieceTransform(FRotator::ZeroRotator, Location, Scale);
            if (bWhite)
            {
                WhitePieceInstances->AddInstance(PieceTransform);
            }
            else
            {
                BlackPieceInstances->AddInstance(PieceTransform);
            }
            ++File;
        }
    }
}

float AChessBoardActor::PieceScaleForFenSymbol(TCHAR Symbol) const
{
    switch (FChar::ToLower(Symbol))
    {
    case TCHAR('p'):
        return 0.72f;
    case TCHAR('n'):
    case TCHAR('b'):
        return 0.84f;
    case TCHAR('r'):
        return 0.92f;
    case TCHAR('q'):
        return 1.00f;
    case TCHAR('k'):
        return 1.08f;
    default:
        return 0.88f;
    }
}

void AChessBoardActor::ApplyDefaultMaterials()
{
    if (TileMaterial == nullptr)
    {
        return;
    }

    auto MakeTinted = [this](const FLinearColor& Color) -> UMaterialInterface*
    {
        UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(TileMaterial, this);
        if (Dynamic != nullptr)
        {
            Dynamic->SetVectorParameterValue(TEXT("Color"), Color);
            Dynamic->SetVectorParameterValue(TEXT("BaseColor"), Color);
        }
        return Dynamic != nullptr ? Dynamic : TileMaterial;
    };

    LightTileInstances->SetMaterial(0, MakeTinted(FLinearColor(0.88f, 0.9f, 0.95f)));
    DarkTileInstances->SetMaterial(0, MakeTinted(FLinearColor(0.18f, 0.22f, 0.3f)));
    WhitePieceInstances->SetMaterial(0, MakeTinted(FLinearColor(0.95f, 0.97f, 1.0f)));
    BlackPieceInstances->SetMaterial(0, MakeTinted(FLinearColor(0.08f, 0.1f, 0.14f)));
}

bool AChessBoardActor::IsSquareValid(const FString& Square) const
{
    if (Square.Len() != 2)
    {
        return false;
    }

    const TCHAR File = Square[0];
    const TCHAR Rank = Square[1];
    return File >= TCHAR('a') && File <= TCHAR('h') && Rank >= TCHAR('1') && Rank <= TCHAR('8');
}

FString AChessBoardActor::NormalizeSquare(const FString& Square) const
{
    return Square.ToLower().TrimStartAndEnd();
}
