// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/ui/webui/help/github_release.h"

#include "base/strings/string_number_conversions.h"
#include "base/strings/string_util.h"
#include "base/time/time.h"

namespace joao_browser {

bool IsValidReleaseVersion(std::string_view version) {
  if (version.size() != 14 ||
      version.find_first_not_of("0123456789") != std::string_view::npos) {
    return false;
  }
  base::Time::Exploded exploded = {};
  base::StringToInt(version.substr(0, 4), &exploded.year);
  base::StringToInt(version.substr(4, 2), &exploded.month);
  base::StringToInt(version.substr(6, 2), &exploded.day_of_month);
  base::StringToInt(version.substr(8, 2), &exploded.hour);
  base::StringToInt(version.substr(10, 2), &exploded.minute);
  base::StringToInt(version.substr(12, 2), &exploded.second);
  if (exploded.year < 2020 || exploded.second > 59 ||
      !exploded.HasValidValues()) {
    return false;
  }
  base::Time time;
  if (!base::Time::FromUTCExploded(exploded, &time)) {
    return false;
  }
  base::Time::Exploded normalized;
  time.UTCExplode(&normalized);
  return normalized.year == exploded.year &&
         normalized.month == exploded.month &&
         normalized.day_of_month == exploded.day_of_month &&
         normalized.hour == exploded.hour &&
         normalized.minute == exploded.minute &&
         normalized.second == exploded.second;
}

bool IsNewerReleaseVersion(std::string_view candidate,
                           std::string_view current) {
  return IsValidReleaseVersion(candidate) && IsValidReleaseVersion(current) &&
         candidate > current;
}

std::optional<GitHubRelease> ParseGitHubRelease(const base::DictValue& release,
                                                bool portable) {
  const std::string* tag = release.FindString("tag_name");
  const std::string* published = release.FindString("published_at");
  const base::ListValue* assets = release.FindList("assets");
  if (release.FindBool("draft") != false ||
      release.FindBool("prerelease") != false || !published ||
      published->empty() || !tag || !base::StartsWith(*tag, "joao-v") ||
      !IsValidReleaseVersion(std::string_view(*tag).substr(6)) || !assets) {
    return std::nullopt;
  }
  const std::string asset_name = "JoaoBrowser-" + *tag + "-windows-x64-" +
                                 (portable ? "portable.zip" : "offline.exe");
  const std::string expected_url =
      "https://github.com/JoaoDEVWHADS/joao-browser/releases/download/" + *tag +
      "/" + asset_name;
  for (const auto& asset : *assets) {
    const auto* dict = asset.GetIfDict();
    if (!dict) {
      continue;
    }
    const std::string* name = dict->FindString("name");
    const std::string* url = dict->FindString("browser_download_url");
    const std::string* state = dict->FindString("state");
    if (name && *name == asset_name && url && *url == expected_url && state &&
        *state == "uploaded") {
      return GitHubRelease{tag->substr(6), GURL(*url)};
    }
  }
  return std::nullopt;
}

}  // namespace joao_browser
