#include "ChessCameraDirector.h"

#include "Camera/CameraComponent.h"
#include "ChessGameStateComponent.h"
#include "Components/SceneComponent.h"
#include "Kismet/KismetMathLibrary.h"

AChessCameraDirector::AChessCameraDirector()
{
    PrimaryActorTick.bCanEverTick = true;

    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(Root);
}

void AChessCameraDirector::BeginPlay()
{
    Super::BeginPlay();

    if (GameStateComponent != nullptr)
    {
        GameStateComponent->OnStateChanged.AddDynamic(this, &AChessCameraDirector::HandleStateChanged);
        ApplySideToMove(GameStateComponent->CurrentState.Turn);
    }
    else
    {
        ApplySideToMove(TEXT("white"));
    }

    SetActorLocationAndRotation(TargetEye, TargetRotation);
}

void AChessCameraDirector::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    const FVector NewLocation = FMath::VInterpTo(GetActorLocation(), TargetEye, DeltaSeconds, LerpSpeed);
    const FRotator NewRotation = FMath::RInterpTo(GetActorRotation(), TargetRotation, DeltaSeconds, LerpSpeed);
    SetActorLocationAndRotation(NewLocation, NewRotation);
}

void AChessCameraDirector::ApplySideToMove(const FString& Turn)
{
    const bool bWhiteToMove = Turn.Equals(TEXT("white"), ESearchCase::IgnoreCase);
    TargetEye = bWhiteToMove ? WhiteEye : BlackEye;
    TargetRotation = UKismetMathLibrary::FindLookAtRotation(TargetEye, LookTarget);
}

void AChessCameraDirector::HandleStateChanged()
{
    if (GameStateComponent == nullptr)
    {
        return;
    }
    ApplySideToMove(GameStateComponent->CurrentState.Turn);
}
