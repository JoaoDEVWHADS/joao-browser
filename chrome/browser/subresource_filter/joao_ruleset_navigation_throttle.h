// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef CHROME_BROWSER_SUBRESOURCE_FILTER_JOAO_RULESET_NAVIGATION_THROTTLE_H_
#define CHROME_BROWSER_SUBRESOURCE_FILTER_JOAO_RULESET_NAVIGATION_THROTTLE_H_

namespace content {
class NavigationThrottleRegistry;
}

namespace joao_adblock {

void MaybeAddRulesetNavigationThrottle(
    content::NavigationThrottleRegistry& registry);

}  // namespace joao_adblock

#endif  // CHROME_BROWSER_SUBRESOURCE_FILTER_JOAO_RULESET_NAVIGATION_THROTTLE_H_
