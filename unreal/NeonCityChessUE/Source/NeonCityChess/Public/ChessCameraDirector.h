#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ChessCameraDirector.generated.h"

class UChessGameStateComponent;
class UCameraComponent;
class USceneComponent;

UCLASS()
class NEONCITYCHESS_API AChessCameraDirector : public AActor
{
    GENERATED_BODY()

public:
    AChessCameraDirector();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess")
    TObjectPtr<USceneComponent> Root;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess")
    TObjectPtr<UCameraComponent> Camera;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    TObjectPtr<UChessGameStateComponent> GameStateComponent;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    FVector WhiteEye = FVector(-850.0f, 0.0f, 650.0f);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    FVector BlackEye = FVector(850.0f, 0.0f, 650.0f);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    FVector LookTarget = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    float LerpSpeed = 4.5f;

    UFUNCTION(BlueprintCallable, Category = "Chess")
    void ApplySideToMove(const FString& Turn);

private:
    UFUNCTION()
    void HandleStateChanged();

    FVector TargetEye = FVector::ZeroVector;
    FRotator TargetRotation = FRotator::ZeroRotator;
};
