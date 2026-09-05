// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/ui/webui/help/github_release.h"

#include "testing/gtest/include/gtest/gtest.h"

namespace joao_browser {
namespace {

base::DictValue Release() {
  base::ListValue assets;
  for (const char* suffix : {"offline.exe", "portable.zip"}) {
    const std::string name =
        std::string("JoaoBrowser-joao-v20260905123059-windows-x64-") + suffix;
    assets.Append(base::DictValue()
                      .Set("name", name)
                      .Set("state", "uploaded")
                      .Set("browser_download_url",
                           "https://github.com/JoaoDEVWHADS/joao-browser/"
                           "releases/download/joao-v20260905123059/" +
                               name));
  }
  return base::DictValue()
      .Set("tag_name", "joao-v20260905123059")
      .Set("draft", false)
      .Set("prerelease", false)
      .Set("published_at", "2026-09-05T12:31:00Z")
      .Set("assets", std::move(assets));
}

TEST(JoaoGitHubReleaseTest, SelectsMatchingDistribution) {
  auto installed = ParseGitHubRelease(Release(), false);
  auto portable = ParseGitHubRelease(Release(), true);
  ASSERT_TRUE(installed);
  ASSERT_TRUE(portable);
  EXPECT_EQ(installed->version, "20260905123059");
  EXPECT_TRUE(installed->download_url.path().ends_with("offline.exe"));
  EXPECT_TRUE(portable->download_url.path().ends_with("portable.zip"));
}

TEST(JoaoGitHubReleaseTest, RejectsUnpublishedAndPrerelease) {
  for (const char* key : {"draft", "prerelease"}) {
    auto release = Release();
    release.Set(key, true);
    EXPECT_FALSE(ParseGitHubRelease(release, false));
  }
  auto release = Release();
  release.Remove("published_at");
  EXPECT_FALSE(ParseGitHubRelease(release, false));
}

TEST(JoaoGitHubReleaseTest, RejectsForeignAndUnsafeAssetUrls) {
  for (const char* url :
       {"https://github.com/attacker/joao-browser/releases/download/file.exe",
        "http://github.com/JoaoDEVWHADS/joao-browser/file.exe",
        "https://github.com.evil.test/file.exe", "javascript:alert(1)"}) {
    auto release = Release();
    (*release.FindList("assets"))[0].GetDict().Set("browser_download_url", url);
    EXPECT_FALSE(ParseGitHubRelease(release, false));
  }
}

TEST(JoaoGitHubReleaseTest, RejectsIncompleteAssetsAndMalformedTags) {
  auto release = Release();
  (*release.FindList("assets"))[0].GetDict().Set("state", "new");
  EXPECT_FALSE(ParseGitHubRelease(release, false));
  for (const char* tag : {"main", "joao-v20260230120000", "joao-v155.0.8044.0",
                          "joao-v20260905123059/../../bad"}) {
    auto invalid = Release();
    invalid.Set("tag_name", tag);
    EXPECT_FALSE(ParseGitHubRelease(invalid, false));
  }
}

TEST(JoaoGitHubReleaseTest, ValidatesCalendarAndTime) {
  EXPECT_TRUE(IsValidReleaseVersion("20240229120000"));
  for (const char* version :
       {"20230229120000", "20260230120000", "20260905240000", "20260905126000",
        "20260905120060", "2026090512000x", "0"}) {
    EXPECT_FALSE(IsValidReleaseVersion(version));
  }
}

TEST(JoaoGitHubReleaseTest, NeverOffersEqualOrOlderRelease) {
  EXPECT_TRUE(IsNewerReleaseVersion("20260905123059", "20260905123058"));
  EXPECT_FALSE(IsNewerReleaseVersion("20260905123059", "20260905123059"));
  EXPECT_FALSE(IsNewerReleaseVersion("20260905123058", "20260905123059"));
  EXPECT_FALSE(IsNewerReleaseVersion("20260905243000", "20260905123059"));
}

}  // namespace
}  // namespace joao_browser
