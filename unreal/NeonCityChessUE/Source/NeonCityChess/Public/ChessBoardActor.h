#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ChessBoardActor.generated.h"

class UChessGameStateComponent;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
class USceneComponent;
class UStaticMesh;

UCLASS()
class NEONCITYCHESS_API AChessBoardActor : public AActor
{
    GENERATED_BODY()

public:
    AChessBoardActor();
    virtual void BeginPlay() override;
    virtual void OnConstruction(const FTransform& Transform) override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess")
    TObjectPtr<USceneComponent> Root;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    TObjectPtr<UChessGameStateComponent> GameStateComponent;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess|Visuals")
    TObjectPtr<UInstancedStaticMeshComponent> LightTileInstances;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess|Visuals")
    TObjectPtr<UInstancedStaticMeshComponent> DarkTileInstances;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess|Visuals")
    TObjectPtr<UInstancedStaticMeshComponent> WhitePieceInstances;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Chess|Visuals")
    TObjectPtr<UInstancedStaticMeshComponent> BlackPieceInstances;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    float TileSize = 100.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess|Visuals")
    float TileThickness = 10.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess|Visuals")
    float PieceBaseSize = 62.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess|Visuals")
    float PieceBaseHeight = 86.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess")
    FVector BoardOrigin = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess|Visuals")
    TObjectPtr<UStaticMesh> BoardMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chess|Visuals")
    TObjectPtr<UMaterialInterface> TileMaterial;

    UFUNCTION(BlueprintPure, Category = "Chess")
    FVector SquareToWorld(const FString& Square, float HeightOffset = 0.0f) const;

    UFUNCTION(BlueprintPure, Category = "Chess")
    bool WorldToSquare(const FVector& WorldLocation, FString& OutSquare) const;

    UFUNCTION(BlueprintCallable, Category = "Chess")
    bool ClickWorldLocation(const FVector& WorldLocation, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "Chess|Visuals")
    void RebuildVisuals();

private:
    UFUNCTION()
    void HandleStateChanged();

    bool TryResolveGameStateComponent();
    void BuildBoardTiles();
    void RebuildPiecesFromFen(const FString& Fen);
    float PieceScaleForFenSymbol(TCHAR Symbol) const;
    void ApplyDefaultMaterials();
    bool IsSquareValid(const FString& Square) const;
    FString NormalizeSquare(const FString& Square) const;
};
