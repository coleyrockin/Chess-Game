#include "ChessGameStateComponent.h"

#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
FString QuoteArg(const FString& In)
{
    FString Out = In;
    Out.ReplaceInline(TEXT("\""), TEXT("\\\""));
    return FString::Printf(TEXT("\"%s\""), *Out);
}
} // namespace

UChessGameStateComponent::UChessGameStateComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    PythonExecutable.FilePath = TEXT("python3");
}

void UChessGameStateComponent::BeginPlay()
{
    Super::BeginPlay();

    FString Error;
    RefreshState(Error);
    if (!Error.IsEmpty())
    {
        UE_LOG(LogTemp, Warning, TEXT("Chess state initialization warning: %s"), *Error);
    }
}

bool UChessGameStateComponent::RefreshState(FString& OutError)
{
    OutError.Empty();

    const FString PythonExe = PythonExecutable.FilePath.IsEmpty() ? TEXT("python3") : PythonExecutable.FilePath;

    FString ScriptPath;
    if (!ExportScriptPath.FilePath.IsEmpty())
    {
        ScriptPath = FPaths::ConvertRelativePathToFull(ExportScriptPath.FilePath);
    }
    else
    {
        // Default fallback: project sits under unreal/NeonCityChessUE and exporter is at unreal/export_state.py.
        ScriptPath = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("../export_state.py")));
    }

    if (!FPaths::FileExists(ScriptPath))
    {
        OutError = FString::Printf(
            TEXT("Export script not found at '%s'. Set ExportScriptPath to your unreal/export_state.py."),
            *ScriptPath);
        return false;
    }

    FString WorkingDir = WorkingDirectory.Path;
    if (WorkingDir.IsEmpty())
    {
        WorkingDir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("../..")));
    }

    const FString OutputDir = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Chess"));
    IFileManager::Get().MakeDirectory(*OutputDir, true);
    const FString OutputPath = FPaths::Combine(OutputDir, TEXT("state_payload.json"));

    const FString Params = FString::Printf(
        TEXT("%s --fen %s --moves %s --output %s"),
        *QuoteArg(ScriptPath),
        *QuoteArg(StartFen),
        *QuoteArg(BuildMovesCsv()),
        *QuoteArg(OutputPath));

    int32 ReturnCode = -1;
    FString StdOut;
    FString StdErr;
    const bool bExecOk = FPlatformProcess::ExecProcess(
        *PythonExe,
        *Params,
        &ReturnCode,
        &StdOut,
        &StdErr,
        *WorkingDir);

    if (!bExecOk || ReturnCode != 0)
    {
        OutError = FString::Printf(
            TEXT("Failed to run exporter (code=%d). StdErr: %s StdOut: %s"),
            ReturnCode,
            *StdErr,
            *StdOut);
        return false;
    }

    FString Json;
    if (!FFileHelper::LoadFileToString(Json, *OutputPath))
    {
        OutError = FString::Printf(TEXT("Failed to read output JSON: %s"), *OutputPath);
        return false;
    }

    FChessStatePayload NextState;
    if (!ParsePayloadJson(Json, NextState, OutError))
    {
        return false;
    }

    CurrentState = MoveTemp(NextState);
    OnStateChanged.Broadcast();
    return true;
}

void UChessGameStateComponent::ResetMatch()
{
    MoveHistoryUci.Reset();
    FString Error;
    if (!RefreshState(Error) && !Error.IsEmpty())
    {
        UE_LOG(LogTemp, Warning, TEXT("ResetMatch failed: %s"), *Error);
    }
}

bool UChessGameStateComponent::SelectSquare(const FString& Square)
{
    const FString Normalized = NormalizeSquare(Square);
    if (!IsSquareValid(Normalized))
    {
        return false;
    }

    TArray<FString> NextTargets;
    for (const FString& Uci : CurrentState.LegalMovesUci)
    {
        if (Uci.Len() < 4)
        {
            continue;
        }
        if (Uci.Left(2).Equals(Normalized, ESearchCase::CaseSensitive))
        {
            NextTargets.AddUnique(Uci.Mid(2, 2));
        }
    }

    if (NextTargets.IsEmpty())
    {
        CurrentState.SelectedSquare.Empty();
        CurrentState.LegalTargets.Reset();
        OnStateChanged.Broadcast();
        return false;
    }

    CurrentState.SelectedSquare = Normalized;
    CurrentState.LegalTargets = MoveTemp(NextTargets);
    CurrentState.LegalTargets.Sort();
    OnStateChanged.Broadcast();
    return true;
}

bool UChessGameStateComponent::TryMoveSelectedTo(const FString& TargetSquare, FString& OutError)
{
    OutError.Empty();

    const FString From = NormalizeSquare(CurrentState.SelectedSquare);
    const FString To = NormalizeSquare(TargetSquare);
    if (!IsSquareValid(From))
    {
        OutError = TEXT("No selected square.");
        return false;
    }
    if (!IsSquareValid(To))
    {
        OutError = TEXT("Target square is invalid.");
        return false;
    }

    const FString Prefix = From + To;
    FString SelectedMove;
    for (const FString& Uci : CurrentState.LegalMovesUci)
    {
        if (Uci.StartsWith(Prefix, ESearchCase::CaseSensitive))
        {
            if (Uci.Len() == 5 && Uci[4] == TCHAR('q'))
            {
                SelectedMove = Uci;
                break;
            }
            if (SelectedMove.IsEmpty())
            {
                SelectedMove = Uci;
            }
        }
    }

    if (SelectedMove.IsEmpty())
    {
        OutError = FString::Printf(TEXT("Illegal move: %s"), *Prefix);
        return false;
    }

    MoveHistoryUci.Add(SelectedMove);
    if (!RefreshState(OutError))
    {
        MoveHistoryUci.Pop();
        return false;
    }

    return true;
}

bool UChessGameStateComponent::ParsePayloadJson(const FString& Json, FChessStatePayload& OutState, FString& OutError) const
{
    TSharedPtr<FJsonObject> RootObj;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
    if (!FJsonSerializer::Deserialize(Reader, RootObj) || !RootObj.IsValid())
    {
        OutError = TEXT("Failed to parse JSON payload.");
        return false;
    }

    if (!RootObj->TryGetStringField(TEXT("fen"), OutState.Fen) ||
        !RootObj->TryGetStringField(TEXT("turn"), OutState.Turn) ||
        !RootObj->TryGetBoolField(TEXT("is_game_over"), OutState.bIsGameOver) ||
        !RootObj->TryGetStringField(TEXT("status_text"), OutState.StatusText) ||
        !RootObj->TryGetStringField(TEXT("score_text"), OutState.ScoreText))
    {
        OutError = TEXT("Payload is missing one or more required fields.");
        return false;
    }

    RootObj->TryGetStringField(TEXT("selected_square"), OutState.SelectedSquare);

    const TArray<TSharedPtr<FJsonValue>>* LegalTargetsJson = nullptr;
    if (RootObj->TryGetArrayField(TEXT("legal_targets"), LegalTargetsJson) && LegalTargetsJson != nullptr)
    {
        OutState.LegalTargets.Reset();
        for (const TSharedPtr<FJsonValue>& Item : *LegalTargetsJson)
        {
            FString Value;
            if (Item.IsValid() && Item->TryGetString(Value))
            {
                OutState.LegalTargets.Add(Value);
            }
        }
    }

    const TArray<TSharedPtr<FJsonValue>>* LegalMovesJson = nullptr;
    if (RootObj->TryGetArrayField(TEXT("legal_moves_uci"), LegalMovesJson) && LegalMovesJson != nullptr)
    {
        OutState.LegalMovesUci.Reset();
        for (const TSharedPtr<FJsonValue>& Item : *LegalMovesJson)
        {
            FString Value;
            if (Item.IsValid() && Item->TryGetString(Value))
            {
                OutState.LegalMovesUci.Add(Value);
            }
        }
    }

    return true;
}

bool UChessGameStateComponent::IsSquareValid(const FString& Square) const
{
    if (Square.Len() != 2)
    {
        return false;
    }

    const TCHAR File = Square[0];
    const TCHAR Rank = Square[1];
    return File >= TCHAR('a') && File <= TCHAR('h') && Rank >= TCHAR('1') && Rank <= TCHAR('8');
}

FString UChessGameStateComponent::NormalizeSquare(const FString& Square) const
{
    return Square.ToLower().TrimStartAndEnd();
}

FString UChessGameStateComponent::BuildMovesCsv() const
{
    FString Out;
    for (int32 Index = 0; Index < MoveHistoryUci.Num(); ++Index)
    {
        if (Index > 0)
        {
            Out.AppendChar(TCHAR(','));
        }
        Out.Append(MoveHistoryUci[Index]);
    }
    return Out;
}
