// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <memory>
#include <optional>
#include <string>

#include "base/functional/bind.h"
#include "base/json/json_reader.h"
#include "base/memory/weak_ptr.h"
#include "base/task/thread_pool.h"
#include "base/time/time.h"
#include "chrome/browser/ui/webui/help/github_release.h"
#include "chrome/browser/ui/webui/help/joao_release_version.h"
#include "chrome/browser/ui/webui/help/version_updater.h"
#include "chrome/grit/generated_resources.h"
#include "chrome/install_static/user_data_dir.h"
#include "content/public/browser/browser_context.h"
#include "content/public/browser/storage_partition.h"
#include "content/public/browser/web_contents.h"
#include "net/base/load_flags.h"
#include "net/http/http_response_headers.h"
#include "net/traffic_annotation/network_traffic_annotation.h"
#include "services/network/public/cpp/resource_request.h"
#include "services/network/public/cpp/shared_url_loader_factory.h"
#include "services/network/public/cpp/simple_url_loader.h"
#include "services/network/public/mojom/fetch_api.mojom.h"
#include "services/network/public/mojom/url_response_head.mojom.h"
#include "ui/base/l10n/l10n_util.h"

namespace {

class VersionUpdaterGitHub : public VersionUpdater {
 public:
  explicit VersionUpdaterGitHub(
      scoped_refptr<network::SharedURLLoaderFactory> factory)
      : factory_(std::move(factory)) {}

  std::string GetDownloadUrl() const override { return download_url_; }
  std::string GetCurrentReleaseVersion() const override {
    return kJoaoReleaseVersion;
  }

  void CheckForUpdate(StatusCallback callback, PromoteCallback) override {
    weak_factory_.InvalidateWeakPtrs();
    loader_.reset();
    download_url_.clear();
    callback_ = std::move(callback);
    Notify(CHECKING);
    base::ThreadPool::PostTaskAndReplyWithResult(
        FROM_HERE, {base::MayBlock(), base::TaskPriority::USER_VISIBLE},
        base::BindOnce([] {
          std::wstring directory;
          return install_static::GetPortableUserDataDirectory(&directory);
        }),
        base::BindOnce(&VersionUpdaterGitHub::FetchRelease,
                       weak_factory_.GetWeakPtr()));
  }

 private:
  void FetchRelease(bool portable) {
    portable_ = portable;
    if (!factory_) {
      Fail();
      return;
    }
    auto request = std::make_unique<network::ResourceRequest>();
    request->url = GURL(joao_browser::kLatestReleaseUrl);
    request->credentials_mode = network::mojom::CredentialsMode::kOmit;
    request->load_flags = net::LOAD_DISABLE_CACHE;
    request->headers.SetHeader("Accept", "application/vnd.github+json");
    request->headers.SetHeader("X-GitHub-Api-Version", "2022-11-28");
    request->headers.SetHeader("User-Agent", "Joao-Browser-Update-Checker");
    constexpr auto annotation =
        net::DefineNetworkTrafficAnnotation("joao_browser_release_check", R"(
      semantics {
        sender: "Joao Browser update checker"
        description: "Checks the latest published Joao Browser GitHub release."
        trigger: "Opening the About page or refreshing its update status."
        data: "A public GitHub API request; no cookies or profile identifiers."
        destination: OTHER
        destination_other: "api.github.com"
      }
      policy {
        cookies_allowed: NO
        setting: "The check only occurs when the user opens the About page."
        policy_exception_justification: "User-initiated public release lookup."
      })");
    loader_ = network::SimpleURLLoader::Create(std::move(request), annotation);
    loader_->SetTimeoutDuration(base::Seconds(30));
    loader_->DownloadToString(factory_.get(),
                              base::BindOnce(&VersionUpdaterGitHub::OnRelease,
                                             weak_factory_.GetWeakPtr()),
                              1024 * 1024);
  }

  void OnRelease(std::optional<std::string> body) {
    if (!body || !loader_->ResponseInfo() ||
        !loader_->ResponseInfo()->headers ||
        loader_->ResponseInfo()->headers->response_code() != 200 ||
        loader_->GetFinalURL() != GURL(joao_browser::kLatestReleaseUrl)) {
      Fail();
      return;
    }
    auto value = base::JSONReader::ReadDict(*body, base::JSON_PARSE_RFC);
    auto release = value ? joao_browser::ParseGitHubRelease(*value, portable_)
                         : std::nullopt;
    loader_.reset();
    if (!release) {
      Fail();
      return;
    }
    if (!joao_browser::IsNewerReleaseVersion(release->version,
                                             kJoaoReleaseVersion)) {
      Notify(UPDATED);
      return;
    }
    download_url_ = release->download_url.spec();
    callback_.Run(UPDATE_AVAILABLE, 0, false, false, release->version, 0,
                  l10n_util::GetStringUTF16(
                      portable_ ? IDS_SETTINGS_JOAO_UPDATE_PORTABLE
                                : IDS_SETTINGS_JOAO_UPDATE_INSTALLED));
  }

  void Fail() {
    loader_.reset();
    callback_.Run(FAILED, 0, false, false, std::string(), 0,
                  l10n_util::GetStringUTF16(IDS_SETTINGS_JOAO_UPDATE_FAILED));
  }

  void Notify(Status status) {
    callback_.Run(status, 0, false, false, std::string(), 0, std::u16string());
  }

  scoped_refptr<network::SharedURLLoaderFactory> factory_;
  std::unique_ptr<network::SimpleURLLoader> loader_;
  StatusCallback callback_;
  std::string download_url_;
  bool portable_ = false;
  base::WeakPtrFactory<VersionUpdaterGitHub> weak_factory_{this};
};

}  // namespace

std::unique_ptr<VersionUpdater> VersionUpdater::Create(
    content::WebContents* web_contents) {
  return std::make_unique<VersionUpdaterGitHub>(
      web_contents ? web_contents->GetBrowserContext()
                         ->GetDefaultStoragePartition()
                         ->GetURLLoaderFactoryForBrowserProcess()
                   : nullptr);
}
