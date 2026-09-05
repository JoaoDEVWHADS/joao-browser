// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/subresource_filter/joao_ruleset_navigation_throttle.h"

#include <memory>

#include "base/callback_list.h"
#include "base/feature_list.h"
#include "base/functional/bind.h"
#include "base/memory/raw_ref.h"
#include "base/memory/weak_ptr.h"
#include "base/time/time.h"
#include "base/timer/timer.h"
#include "chrome/browser/browser_process.h"
#include "components/subresource_filter/content/browser/ruleset_service.h"
#include "components/subresource_filter/core/common/common_features.h"
#include "content/public/browser/navigation_handle.h"
#include "content/public/browser/navigation_throttle.h"
#include "content/public/browser/navigation_throttle_registry.h"
#include "net/base/net_errors.h"

namespace joao_adblock {
namespace {

class RulesetNavigationThrottle : public content::NavigationThrottle {
 public:
  RulesetNavigationThrottle(content::NavigationThrottleRegistry& registry,
                            subresource_filter::RulesetService& service)
      : content::NavigationThrottle(registry), service_(service) {}

  ThrottleCheckResult WillStartRequest() override {
    if (service_->IsJoaoRulesetReady()) {
      return PROCEED;
    }
    if (!service_->IsJoaoRulesetPending()) {
      return {CANCEL, net::ERR_BLOCKED_BY_CLIENT};
    }
    subscription_ = service_->AddJoaoRulesetReadyCallback(base::BindOnce(
        &RulesetNavigationThrottle::OnReady, weak_factory_.GetWeakPtr()));
    timeout_.Start(FROM_HERE, base::Seconds(30),
                   base::BindOnce(&RulesetNavigationThrottle::OnReady,
                                  weak_factory_.GetWeakPtr(), false));
    return DEFER;
  }

  const char* GetNameForLogging() override {
    return "JoaoRulesetNavigationThrottle";
  }

 private:
  void OnReady(bool success) {
    timeout_.Stop();
    subscription_ = {};
    if (success) {
      Resume();
    } else {
      CancelDeferredNavigation({CANCEL, net::ERR_BLOCKED_BY_CLIENT});
    }
  }

  const raw_ref<subresource_filter::RulesetService> service_;
  base::CallbackListSubscription subscription_;
  base::OneShotTimer timeout_;
  base::WeakPtrFactory<RulesetNavigationThrottle> weak_factory_{this};
};

}  // namespace

void MaybeAddRulesetNavigationThrottle(
    content::NavigationThrottleRegistry& registry) {
  if (!base::FeatureList::IsEnabled(subresource_filter::kJoaoNativeAdblock) ||
      !registry.GetNavigationHandle().IsInMainFrame() ||
      !registry.GetNavigationHandle().GetURL().SchemeIsHTTPOrHTTPS()) {
    return;
  }
  if (auto* service = g_browser_process->subresource_filter_ruleset_service()) {
    registry.AddThrottle(
        std::make_unique<RulesetNavigationThrottle>(registry, *service));
  }
}

}  // namespace joao_adblock
