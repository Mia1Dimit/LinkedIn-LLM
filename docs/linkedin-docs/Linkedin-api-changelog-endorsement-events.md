---
layout: Conceptual
monikers:
- li-dma-data-portability-unversioned
- li-dma-data-portability-2024-05
- li-dma-data-portability-2024-08
- li-dma-data-portability-2024-11
- li-dma-data-portability-2025-02
- li-dma-data-portability-2025-05
- li-dma-data-portability-2025-08
- li-dma-data-portability-2025-11
defaultMoniker: li-dma-data-portability-2025-11
versioningType: Ranged
title: Endorsement Changelog Events - LinkedIn | Microsoft Learn
canonicalUrl: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/shared/changelog-resource-references/endorsement?view=li-dma-data-portability-2025-11
config_moniker_range: li-dma-data-portability-unversioned || li-dma-data-portability-2024-05 || li-dma-data-portability-2024-08 || li-dma-data-portability-2024-11 || li-dma-data-portability-2025-02 || li-dma-data-portability-2025-05 || li-dma-data-portability-2025-08 || li-dma-data-portability-2025-11
breadcrumb_path: /linkedin/breadcrumb/toc.json
recommendations: false
feedback_system: Standard
feedback_product_url: https://linkedin.zendesk.com/hc/en-us
uhfHeaderId: MSDocsHeader-LinkedIn
description: Resource References for Endorsement in Changelog Events
author: sidd607
ms.author: li_akvenkat
ms.date: 2024-03-05T00:00:00.0000000Z
ms.topic: article
ms.service: linkedin
ROBOTS: NOINDEX
locale: en-us
document_id: 53e7b1bc-00f9-0567-6379-84f500178800
document_version_independent_id: 53e7b1bc-00f9-0567-6379-84f500178800
updated_at: 2025-08-29T03:45:00.0000000Z
original_content_git_url: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/live/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/endorsement.md
gitcommit: https://github.com/MicrosoftDocs/linkedin-api-docs/blob/d706d2fef7721b65628388a6e71d4a735acdf57a/linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/endorsement.md
git_commit_id: d706d2fef7721b65628388a6e71d4a735acdf57a
default_moniker: li-dma-data-portability-2025-11
site_name: Docs
depot_name: MSDN.linkedin-api-docs
page_type: conceptual
toc_rel: ../../toc.json
feedback_help_link_type: ''
feedback_help_link_url: ''
word_count: 96
asset_id: dma/member-data-portability/shared/changelog-resource-references/endorsement
moniker_range_name: 0e594fa083335bf635988665e9387b75
monikers:
- li-dma-data-portability-unversioned
- li-dma-data-portability-2024-05
- li-dma-data-portability-2024-08
- li-dma-data-portability-2024-11
- li-dma-data-portability-2025-02
- li-dma-data-portability-2025-05
- li-dma-data-portability-2025-08
- li-dma-data-portability-2025-11
item_type: Content
source_path: linkedin-api-docs/DMA/member-data-portability/shared/changelog-resource-references/endorsement.md
platformId: 139757dd-1650-5ade-4833-a0aa44274487
---

# Endorsement Changelog Events - LinkedIn | Microsoft Learn

The identity of the `resourceName` is `endorsement`. Currently, this resource captures all endorsements the member gives. An endorsement is shown on the member's profile page where there is a set of featured skills and your connections can endorse you for those set of skills. See examples below:

## Endorsement Activity - Endorse a skill

```json
{
  "owner": "urn:li:person:KPA1hpZ1yM",
  "configVersion": 2,
  "method": "CREATE",
  "activity": {
    "item": {
      "nonStandardEntity": {
        "entityType": "PROFILE_SKILL",
        "entityPhrase": "Node.js"
      }
    },
    "endorser": "urn:li:person:KPA1hpZ1yM",
    "recipient": "urn:li:person:V9W_L_bioc",
    "location": "neptune-skills-section",
    "status": "ACCEPTED"
  },
  "resourceName": "endorsement",
  "resourceUri": "/endorsement/urn:li:endorsement:(urn:li:person:V9W_L_bioc,65761962366)",
  "actor": "urn:li:person:KPA1hpZ1yM",
  "processedAt": 1489511042014,
  "capturedAt": 1489511033748,
  "id": 425820,
  "activityId": "12356788990000"
}
```