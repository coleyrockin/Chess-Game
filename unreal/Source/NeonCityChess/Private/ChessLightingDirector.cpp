#include "ChessLightingDirector.h"

#include "ChessGameStateComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"

AChessLightingDirector::AChessLightingDirector()
{
    PrimaryActorTick.bCanEverTick = false;

    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    WhiteSideLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("WhiteSideLight"));
    WhiteSideLight->SetupAttachment(Root);
    WhiteSideLight->SetRelativeLocation(FVector(-520.0f, 0.0f, 340.0f));
    WhiteSideLight->SetLightColor(FLinearColor(0.35f, 0.75f, 1.0f));

    BlackSideLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("BlackSideLight"));
    BlackSideLight->SetupAttachment(Root);
    BlackSideLight->SetRelativeLocation(FVector(520.0f, 0.0f, 340.0f));
    BlackSideLight->SetLightColor(FLinearColor(1.0f, 0.42f, 0.78f));
}

void AChessLightingDirector::BeginPlay()
{
    Super::BeginPlay();

    if (GameStateComponent != nullptr)
    {
        GameStateComponent->OnStateChanged.AddDynamic(this, &AChessLightingDirector::HandleStateChanged);
        ApplySideToMove(GameStateComponent->CurrentState.Turn);
    }
    else
    {
        ApplySideToMove(TEXT("white"));
    }
}

void AChessLightingDirector::ApplySideToMove(const FString& Turn)
{
    const bool bWhiteToMove = Turn.Equals(TEXT("white"), ESearchCase::IgnoreCase);
    WhiteSideLight->SetIntensity(bWhiteToMove ? ActiveIntensity : PassiveIntensity);
    BlackSideLight->SetIntensity(bWhiteToMove ? PassiveIntensity : ActiveIntensity);
}

void AChessLightingDirector::HandleStateChanged()
{
    if (GameStateComponent == nullptr)
    {
        return;
    }
    ApplySideToMove(GameStateComponent->CurrentState.Turn);
}
