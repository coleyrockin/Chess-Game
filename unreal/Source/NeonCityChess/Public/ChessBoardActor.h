#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ChessBoardActor.generated.h"

class UChessGameStateComponent;

UCLASS()
class NEONCITYCHESS_API AChessBoardActor : public AActor
{
    GENERATED_BODY()

public:
    AChessBoardActor();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    TObjectPtr<UChessGameStateComponent> GameStateComponent;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    float TileSize = 100.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    FVector BoardOrigin = FVector::ZeroVector;

    UFUNCTION(BlueprintPure, Category = "Chess")
    FVector SquareToWorld(const FString& Square, float HeightOffset = 0.0f) const;

    UFUNCTION(BlueprintPure, Category = "Chess")
    bool WorldToSquare(const FVector& WorldLocation, FString& OutSquare) const;

    UFUNCTION(BlueprintCallable, Category = "Chess")
    bool ClickWorldLocation(const FVector& WorldLocation, FString& OutError);

private:
    bool IsSquareValid(const FString& Square) const;
    FString NormalizeSquare(const FString& Square) const;
};
