// Copyright 2024 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/ui/startup/default_browser_prompt/default_browser_prompt_manager.h"

#include <optional>

#include "base/memory/raw_ptr.h"
#include "base/test/run_until.h"
#include "base/test/scoped_feature_list.h"
#include "base/time/time.h"
#include "build/build_config.h"
#include "chrome/browser/browser_process.h"
#include "chrome/browser/default_browser/default_browser_controller.h"
#include "chrome/browser/default_browser/default_browser_features.h"
#include "chrome/browser/ui/startup/default_browser_prompt/default_browser_prompt_prefs.h"
#include "chrome/browser/ui/startup/default_browser_prompt/default_browser_surface_manager.h"
#include "chrome/browser/ui/ui_features.h"
#include "chrome/common/pref_names.h"
#include "components/prefs/pref_service.h"
#include "content/public/test/browser_task_environment.h"
#include "testing/gtest/include/gtest/gtest.h"

class DefaultBrowserPromptManagerTest : public testing::Test {
 public:
  DefaultBrowserPromptManagerTest()
      : task_environment_(base::test::TaskEnvironment::TimeSource::MOCK_TIME) {}

 protected:
  void SetUp() override {
    chrome::startup::default_prompt::ResetPromptPrefs(nullptr);
    local_state()->ClearPref(prefs::kDefaultBrowserPromptDeclined);
    manager_ = DefaultBrowserPromptManager::GetInstance();
    manager_->CloseAllPrompts(
        DefaultBrowserPromptManager::CloseReason::kAccept);
  }

  void TearDown() override {
    chrome::startup::default_prompt::ResetPromptPrefs(nullptr);
    local_state()->ClearPref(prefs::kDefaultBrowserPromptDeclined);
    manager_->CloseAllPrompts(
        DefaultBrowserPromptManager::CloseReason::kAccept);
  }

  void TestShouldShowInfoBarPrompt(
      std::optional<base::TimeDelta> last_declined_time_delta,
      std::optional<int> declined_count,
      bool expect_infobar_exists,
      bool use_framework_prefs = false) {
    const char* time_pref = use_framework_prefs
                                ? prefs::kDefaultBrowserLastDeclinedTime
                                : prefs::kDefaultBrowserInfobarLastDeclinedTime;
    const char* count_pref = use_framework_prefs
                                 ? prefs::kDefaultBrowserDeclinedCount
                                 : prefs::kDefaultBrowserInfobarDeclinedCount;

    if (last_declined_time_delta.has_value()) {
      local_state()->SetTime(
          time_pref, base::Time::Now() - last_declined_time_delta.value());
    } else {
      local_state()->ClearPref(time_pref);
    }
    if (declined_count.has_value()) {
      local_state()->SetInteger(count_pref, declined_count.value());
    } else {
      local_state()->ClearPref(count_pref);
    }

    manager()->CloseAllPrompts(
        DefaultBrowserPromptManager::CloseReason::kAccept);

    bool prompt_shown = manager()->MaybeShowPrompt();
    if (prompt_shown) {
      ASSERT_TRUE(base::test::RunUntil([this]() {
        return manager()->GetPromptSurfaceManager() != nullptr;
      }));
    }

    if (expect_infobar_exists) {
      EXPECT_TRUE(prompt_shown);
      ASSERT_NE(manager()->GetPromptSurfaceManager(), nullptr);
      EXPECT_EQ(manager()->GetPromptSurfaceManager()->GetEntrypointType(),
                default_browser::DefaultBrowserEntrypointType::kStartupInfobar);
    } else {
      if (!prompt_shown) {
        EXPECT_EQ(manager()->GetPromptSurfaceManager(), nullptr);
      } else {
        // Prompt was shown, but using a non-infobar surface (e.g. bubble
        // dialog).
        ASSERT_NE(manager()->GetPromptSurfaceManager(), nullptr);
        EXPECT_NE(
            manager()->GetPromptSurfaceManager()->GetEntrypointType(),
            default_browser::DefaultBrowserEntrypointType::kStartupInfobar);
      }
    }
  }

  PrefService* local_state() { return g_browser_process->local_state(); }

  DefaultBrowserPromptManager* manager() { return manager_; }

 protected:
  content::BrowserTaskEnvironment task_environment_;
  base::test::ScopedFeatureList scoped_feature_list_;

 private:
  raw_ptr<DefaultBrowserPromptManager> manager_ = nullptr;
};

TEST_F(DefaultBrowserPromptManagerTest, ShowsAppMenuItem) {
  auto* manager = DefaultBrowserPromptManager::GetInstance();
  ASSERT_FALSE(manager->show_app_menu_item());

  manager->MaybeShowPrompt();
  ASSERT_TRUE(manager->show_app_menu_item());
}

TEST_F(DefaultBrowserPromptManagerTest, AppMenuItemHiddenOnPromptAccept) {
  auto* manager = DefaultBrowserPromptManager::GetInstance();
  manager->MaybeShowPrompt();
  ASSERT_TRUE(manager->show_app_menu_item());

  manager->CloseAllPrompts(DefaultBrowserPromptManager::CloseReason::kAccept);
  ASSERT_FALSE(manager->show_app_menu_item());
}

TEST_F(DefaultBrowserPromptManagerTest, AppMenuItemPersistsOnPromptDismissed) {
  auto* manager = DefaultBrowserPromptManager::GetInstance();
  manager->MaybeShowPrompt();
  ASSERT_TRUE(manager->show_app_menu_item());

  manager->CloseAllPrompts(DefaultBrowserPromptManager::CloseReason::kDismiss);
  ASSERT_TRUE(manager->show_app_menu_item());
}

TEST_F(DefaultBrowserPromptManagerTest, FreshProfileCanSeePrompt) {
  TestShouldShowInfoBarPrompt(std::nullopt, std::nullopt, true);
}

TEST_F(DefaultBrowserPromptManagerTest,
       FirstRunRefusalSuppressesStartupPrompt) {
  local_state()->SetBoolean(prefs::kDefaultBrowserPromptDeclined, true);
  EXPECT_FALSE(manager()->MaybeShowPrompt());
  // The manual app-menu entry remains available.
  EXPECT_TRUE(manager()->show_app_menu_item());
  task_environment_.FastForwardBy(base::Days(3650));
  EXPECT_FALSE(manager()->MaybeShowPrompt());
}

TEST_F(DefaultBrowserPromptManagerTest, LegacyRefusalMigratesPermanently) {
  local_state()->SetInteger(prefs::kDefaultBrowserInfobarDeclinedCount, 1);
  local_state()->SetTime(prefs::kDefaultBrowserInfobarLastDeclinedTime,
                         base::Time::Now() - base::Days(3650));
  EXPECT_FALSE(manager()->MaybeShowPrompt());
  EXPECT_TRUE(local_state()->GetBoolean(prefs::kDefaultBrowserPromptDeclined));
  chrome::startup::default_prompt::ResetPromptPrefs(nullptr);
  EXPECT_FALSE(manager()->MaybeShowPrompt());
}

TEST_F(DefaultBrowserPromptManagerTest, FrameworkRefusalMigratesPermanently) {
  local_state()->SetInteger(prefs::kDefaultBrowserDeclinedCount, 1);
  local_state()->SetTime(prefs::kDefaultBrowserLastDeclinedTime,
                         base::Time::Now() - base::Days(3650));
  EXPECT_FALSE(manager()->MaybeShowPrompt());
  EXPECT_TRUE(local_state()->GetBoolean(prefs::kDefaultBrowserPromptDeclined));
}

TEST_F(DefaultBrowserPromptManagerTest, BecomingDefaultPreservesPastRefusal) {
  local_state()->SetInteger(prefs::kDefaultBrowserInfobarDeclinedCount, 1);
  // Startup resets tracking when the browser becomes the default. A later
  // change to another browser must not erase the user's previous refusal.
  chrome::startup::default_prompt::ResetPromptPrefs(nullptr);
  EXPECT_TRUE(local_state()->GetBoolean(prefs::kDefaultBrowserPromptDeclined));
  EXPECT_FALSE(manager()->MaybeShowPrompt());
}
