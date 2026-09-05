// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef CHROME_BROWSER_UI_WEBUI_HELP_GITHUB_RELEASE_H_
#define CHROME_BROWSER_UI_WEBUI_HELP_GITHUB_RELEASE_H_

#include <optional>
#include <string>
#include <string_view>

#include "base/values.h"
#include "url/gurl.h"

namespace joao_browser {

inline constexpr char kLatestReleaseUrl[] =
    "https://api.github.com/repos/JoaoDEVWHADS/joao-browser/releases/latest";

struct GitHubRelease {
  std::string version;
  GURL download_url;
};

bool IsValidReleaseVersion(std::string_view version);
bool IsNewerReleaseVersion(std::string_view candidate,
                           std::string_view current);
std::optional<GitHubRelease> ParseGitHubRelease(const base::DictValue& release,
                                                bool portable);

}  // namespace joao_browser

#endif  // CHROME_BROWSER_UI_WEBUI_HELP_GITHUB_RELEASE_H_
