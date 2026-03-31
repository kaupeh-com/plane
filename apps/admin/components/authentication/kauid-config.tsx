/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
// icons
import { Settings2 } from "lucide-react";
// plane internal packages
import { getButtonStyling } from "@plane/propel/button";
import type { TInstanceAuthenticationMethodKeys } from "@plane/types";
import { ToggleSwitch } from "@plane/ui";
import { cn } from "@plane/utils";
// hooks
import { useInstance } from "@/hooks/store";

type Props = {
  disabled: boolean;
  updateConfig: (key: TInstanceAuthenticationMethodKeys, value: string) => void;
};

export const KauIDConfiguration = observer(function KauIDConfiguration(props: Props) {
  const { disabled, updateConfig } = props;
  // store
  const { formattedConfig } = useInstance();
  // derived values
  const KauIDConfig = formattedConfig?.IS_KAUID_ENABLED ?? "";
  const KauIDConfigured =
    !!formattedConfig?.KAUID_HOST && !!formattedConfig?.KAUID_CLIENT_ID && !!formattedConfig?.KAUID_CLIENT_SECRET;

  return (
    <>
      {KauIDConfigured ? (
        <div className="flex items-center gap-4">
          <Link href="/authentication/kauid" className={cn(getButtonStyling("link", "base"), "font-medium")}>
            Edit
          </Link>
          <ToggleSwitch
            value={Boolean(parseInt(KauIDConfig))}
            onChange={() => {
              Boolean(parseInt(KauIDConfig)) === true
                ? updateConfig("IS_KAUID_ENABLED", "0")
                : updateConfig("IS_KAUID_ENABLED", "1");
            }}
            size="sm"
            disabled={disabled}
          />
        </div>
      ) : (
        <Link href="/authentication/kauid" className={cn(getButtonStyling("secondary", "base"), "text-tertiary")}>
          <Settings2 className="h-4 w-4 p-0.5 text-tertiary" />
          Configure
        </Link>
      )}
    </>
  );
});
