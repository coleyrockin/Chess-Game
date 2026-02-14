#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/EngineTypes.h"
#include "ChessTypes.h"
#include "ChessGameStateComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnChessStateChanged);

UCLASS(ClassGroup = (Chess), BlueprintType, Blueprintable, meta = (BlueprintSpawnableComponent))
class NEONCITYCHESS_API UChessGameStateComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UChessGameStateComponent();

    virtual void BeginPlay() override;

    UPROPERTY(BlueprintAssignable, Category = "Chess")
    FOnChessStateChanged OnStateChanged;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess")
    FChessStatePayload CurrentState;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess")
    TArray<FString> MoveHistoryUci;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    FString StartFen = TEXT("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess|Python")
    FFilePath PythonExecutable;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess|Python")
    FFilePath ExportScriptPath;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess|Python")
    FDirectoryPath WorkingDirectory;

    UFUNCTION(BlueprintCallable, Category = "Chess")
    bool RefreshState(FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "Chess")
    void ResetMatch();

    UFUNCTION(BlueprintCallable, Category = "Chess")
    bool SelectSquare(const FString& Square);

    UFUNCTION(BlueprintCallable, Category = "Chess")
    bool TryMoveSelectedTo(const FString& TargetSquare, FString& OutError);

private:
    bool ParsePayloadJson(const FString& Json, FChessStatePayload& OutState, FString& OutError) const;
    bool IsSquareValid(const FString& Square) const;
    FString NormalizeSquare(const FString& Square) const;
    FString BuildMovesCsv() const;
};
