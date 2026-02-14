#include "ChessBoardActor.h"

#include "ChessGameStateComponent.h"

AChessBoardActor::AChessBoardActor()
{
    PrimaryActorTick.bCanEverTick = false;
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
