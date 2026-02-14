#pragma once

#include "CoreMinimal.h"
#include "ChessTypes.generated.h"

UENUM(BlueprintType)
enum class EChessSide : uint8
{
    White UMETA(DisplayName = "White"),
    Black UMETA(DisplayName = "Black")
};

USTRUCT(BlueprintType)
struct FChessStatePayload
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, EditAnywhere, Category = "Chess")
    FString Fen;

    UPROPERTY(BlueprintReadOnly, EditAnywhere, Category = "Chess")
    FString Turn;

    UPROPERTY(BlueprintReadOnly, EditAnywhere, Category = "Chess")
    FString SelectedSquare;

    UPROPERTY(BlueprintReadOnly, EditAnywhere, Category = "Chess")
    TArray<FString> LegalTargets;

    UPROPERTY(BlueprintReadOnly, EditAnywhere, Category = "Chess")
    bool bIsGameOver = false;

    UPROPERTY(BlueprintReadOnly, EditAnywhere, Category = "Chess")
    FString StatusText;

    UPROPERTY(BlueprintReadOnly, EditAnywhere, Category = "Chess")
    FString ScoreText;

    UPROPERTY(BlueprintReadOnly, EditAnywhere, Category = "Chess")
    TArray<FString> LegalMovesUci;
};
