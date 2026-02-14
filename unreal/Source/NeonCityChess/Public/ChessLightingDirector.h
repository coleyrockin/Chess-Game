#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ChessLightingDirector.generated.h"

class UChessGameStateComponent;
class UPointLightComponent;
class USceneComponent;

UCLASS()
class NEONCITYCHESS_API AChessLightingDirector : public AActor
{
    GENERATED_BODY()

public:
    AChessLightingDirector();

    virtual void BeginPlay() override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess")
    TObjectPtr<USceneComponent> Root;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess")
    TObjectPtr<UPointLightComponent> WhiteSideLight;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess")
    TObjectPtr<UPointLightComponent> BlackSideLight;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    TObjectPtr<UChessGameStateComponent> GameStateComponent;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    float ActiveIntensity = 16000.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    float PassiveIntensity = 9000.0f;

    UFUNCTION(BlueprintCallable, Category = "Chess")
    void ApplySideToMove(const FString& Turn);

private:
    UFUNCTION()
    void HandleStateChanged();
};
