// Copyright 2018 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "components/subresource_filter/core/common/common_features.h"

#include "build/build_config.h"

namespace subresource_filter {

BASE_FEATURE(kJoaoNativeAdblock,
#if BUILDFLAG(IS_WIN)
             base::FEATURE_ENABLED_BY_DEFAULT
#else
             base::FEATURE_DISABLED_BY_DEFAULT
#endif
);

BASE_FEATURE(kAdTagging, base::FEATURE_ENABLED_BY_DEFAULT);
BASE_FEATURE(kSubresourceFilterPrewarm, base::FEATURE_DISABLED_BY_DEFAULT);

}  // namespace subresource_filter
