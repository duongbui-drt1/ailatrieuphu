APP_NAME = "Ai La Trieu Phu"
APP_VERSION = "2.0.0-beta.1"
APP_AUTHOR = "Duli Production LLC."
APP_COPYRIGHT = "Copyright (c) 2020-2026 Duli Production LLC. All rights reserved."
APP_DESCRIPTION = "Ai La Trieu Phu desktop game show control suite"
APP_PRODUCT_NAME = "Ai La Trieu Phu"
APP_IDENTIFIER_ROOT = "vn.duli.ailatrieuphu"


def version_tuple(version=APP_VERSION):
    parts = []
    for chunk in str(version).split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])
