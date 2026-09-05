#include "components/joao_adblock/rules.h"

#include <string>

#include "base/files/file_util.h"
#include "base/logging.h"
#include "base/strings/string_split.h"
#include "components/joao_adblock/resources.h"
#include "components/subresource_filter/core/common/unindexed_ruleset.h"
#include "components/subresource_filter/tools/rule_parser/rule_parser.h"
#include "third_party/protobuf/src/google/protobuf/io/zero_copy_stream_impl_lite.h"

namespace joao_adblock {
std::string_view RulesVersion() {
  return kVersion;
}

base::FilePath PrepareRules(const base::FilePath& directory) {
  if (!base::CreateDirectory(directory)) {
    return {};
  }
  const auto path = directory.AppendASCII(std::string(kVersion) + ".rules");
  std::string serialized;
  {
    google::protobuf::io::StringOutputStream stream(&serialized);
    subresource_filter::UnindexedRulesetWriter writer(&stream);
    subresource_filter::RuleParser parser;
    size_t accepted = 0;
    size_t unsupported = 0;
    for (auto line : base::SplitStringPiece(kRules, "\n", base::TRIM_WHITESPACE,
                                            base::SPLIT_WANT_NONEMPTY)) {
      if (line.starts_with("!") || line.starts_with("[Adblock") ||
          line.find("##") != std::string_view::npos ||
          line.find("#@#") != std::string_view::npos) {
        continue;
      }
      if (parser.Parse(line) != url_pattern_index::proto::RULE_TYPE_URL) {
        ++unsupported;
        continue;
      }
      if (!writer.AddUrlRule(parser.url_rule().ToProtobuf())) {
        return {};
      }
      ++accepted;
    }
    LOG(INFO) << "Joao adblock: " << accepted << " network rules parsed; "
              << unsupported << " unsupported rules dropped";
    if (!writer.Finish()) {
      return {};
    }
  }
  const auto temporary = path.AddExtensionASCII("tmp");
  if (!base::WriteFile(temporary, serialized) ||
      !base::ReplaceFile(temporary, path, nullptr)) {
    return {};
  }
  return path;
}
}  // namespace joao_adblock
