#ifndef COMPONENTS_JOAO_ADBLOCK_RULES_H_
#define COMPONENTS_JOAO_ADBLOCK_RULES_H_
#include <string_view>

#include "base/files/file_path.h"
namespace joao_adblock {
std::string_view RulesVersion();
// Runs on a blocking sequence. Returns empty on failure.
base::FilePath PrepareRules(const base::FilePath& directory);
}  // namespace joao_adblock
#endif
