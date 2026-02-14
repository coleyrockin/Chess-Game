#pragma once

#include "Modules/ModuleManager.h"

class FNeonCityChessModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
};
