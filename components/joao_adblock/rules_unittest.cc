#include "components/joao_adblock/rules.h"

#include "base/files/file_util.h"
#include "base/files/scoped_temp_dir.h"
#include "components/subresource_filter/core/common/first_party_origin.h"
#include "components/subresource_filter/core/common/indexed_ruleset.h"
#include "components/subresource_filter/core/common/unindexed_ruleset.h"
#include "components/subresource_filter/tools/rule_parser/rule_parser.h"
#include "testing/gtest/include/gtest/gtest.h"
#include "third_party/protobuf/src/google/protobuf/io/zero_copy_stream_impl_lite.h"
#include "url/gurl.h"
#include "url/origin.h"

namespace joao_adblock {
TEST(JoaoAdblock, IndexedMatcherPreservesExceptionsAndRequestScope) {
  subresource_filter::RulesetIndexer indexer(1);
  subresource_filter::RuleParser parser;
  for (auto text : {"||ads.example^$script,third-party",
                    "@@||ads.example/allowed.js$script"}) {
    ASSERT_EQ(url_pattern_index::proto::RULE_TYPE_URL, parser.Parse(text));
    ASSERT_TRUE(indexer.AddUrlRule(parser.url_rule().ToProtobuf()));
  }
  indexer.Finish();
  subresource_filter::IndexedRulesetMatcher matcher(indexer.data());
  auto blocked = [&](const char* target, const char* source,
                     url_pattern_index::proto::ElementType type) {
    return matcher.GetLoadPolicyForResourceLoad(
               GURL(target),
               subresource_filter::FirstPartyOrigin(
                   url::Origin::Create(GURL(source))),
               type, false,
               nullptr) == subresource_filter::LoadPolicy::DISALLOW;
  };
  constexpr auto script = url_pattern_index::proto::ELEMENT_TYPE_SCRIPT;
  EXPECT_TRUE(
      blocked("https://ads.example/ad.js", "https://site.test", script));
  EXPECT_FALSE(
      blocked("https://ads.example/allowed.js", "https://site.test", script));
  EXPECT_FALSE(
      blocked("https://ads.example/ad.js", "https://ads.example", script));
  EXPECT_FALSE(blocked("https://ads.example/ad.js", "https://site.test",
                       url_pattern_index::proto::ELEMENT_TYPE_IMAGE));
  EXPECT_FALSE(blocked("https://ads.example.evil.test/ad.js",
                       "https://site.test", script));
}

TEST(JoaoAdblock, UnsupportedOperatorsAreRejectedRatherThanBroadened) {
  subresource_filter::RuleParser parser;
  EXPECT_EQ(url_pattern_index::proto::RULE_TYPE_UNSPECIFIED,
            parser.Parse("||example.com^$redirect=noopjs"));
  EXPECT_EQ(url_pattern_index::proto::RULE_TYPE_URL,
            parser.Parse("||ads.example^$domain=site.test|~allowed.site.test"));
  subresource_filter::RulesetIndexer indexer(1);
  ASSERT_TRUE(indexer.AddUrlRule(parser.url_rule().ToProtobuf()));
  indexer.Finish();
  subresource_filter::IndexedRulesetMatcher matcher(indexer.data());
  for (auto source : {"https://allowed.site.test", "https://other.test"}) {
    EXPECT_EQ(
        subresource_filter::LoadPolicy::ALLOW,
        matcher.GetLoadPolicyForResourceLoad(
            GURL("https://ads.example/ad.js"),
            subresource_filter::FirstPartyOrigin(
                url::Origin::Create(GURL(source))),
            url_pattern_index::proto::ELEMENT_TYPE_SCRIPT, false, nullptr));
  }
}

TEST(JoaoAdblock, BundledSnapshotProducesRealIndexedRules) {
  base::ScopedTempDir temporary;
  ASSERT_TRUE(temporary.CreateUniqueTempDir());
  const auto path = PrepareRules(temporary.GetPath());
  ASSERT_FALSE(path.empty());
  std::string data;
  ASSERT_TRUE(base::ReadFileToString(path, &data));
  google::protobuf::io::ArrayInputStream stream(data.data(), data.size());
  subresource_filter::UnindexedRulesetReader reader(&stream);
  url_pattern_index::proto::FilteringRules chunk;
  subresource_filter::RulesetIndexer indexer(1);
  size_t indexed = 0;
  while (reader.ReadNextChunk(&chunk)) {
    for (const auto& rule : chunk.url_rules()) {
      indexed += indexer.AddUrlRule(rule);
    }
  }
  EXPECT_GT(indexed, 10000u);
  indexer.Finish();
  subresource_filter::IndexedRulesetMatcher matcher(indexer.data());
  EXPECT_EQ(subresource_filter::LoadPolicy::DISALLOW,
            matcher.GetLoadPolicyForResourceLoad(
                GURL("https://ad.doubleclick.net/ads.js"),
                subresource_filter::FirstPartyOrigin(
                    url::Origin::Create(GURL("https://example.com"))),
                url_pattern_index::proto::ELEMENT_TYPE_SCRIPT, false, nullptr));
  EXPECT_EQ(path, PrepareRules(temporary.GetPath()));
}
}  // namespace joao_adblock
